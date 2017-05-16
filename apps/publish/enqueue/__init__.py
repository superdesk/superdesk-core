# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import cProfile
import logging
import superdesk

from superdesk import get_resource_service
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, PUBLISH_SCHEDULE, SCHEDULE_SETTINGS
from apps.archive.common import ITEM_OPERATION, ARCHIVE, insert_into_versions
from apps.legal_archive.commands import import_into_legal_archive
from apps.publish.enqueue.enqueue_corrected import EnqueueCorrectedService
from apps.publish.enqueue.enqueue_killed import EnqueueKilledService
from apps.publish.enqueue.enqueue_published import EnqueuePublishedService
from apps.publish.published_item import PUBLISH_STATE, QUEUE_STATE, PUBLISHED, ERROR_MESSAGE
from bson.objectid import ObjectId
from eve.utils import config, ParsedRequest
from eve.versioning import resolve_document_version
from superdesk.celery_app import celery
from superdesk.utc import utcnow
from superdesk.profiling import ProfileManager
from apps.content import push_content_notification
from superdesk.errors import ConnectionTimeout


logger = logging.getLogger(__name__)

profile = cProfile.Profile()

UPDATE_SCHEDULE_DEFAULT = {'seconds': 10}

ITEM_PUBLISH = 'publish'
ITEM_CORRECT = 'correct'
ITEM_KILL = 'kill'

enqueue_services = {
    ITEM_PUBLISH: EnqueuePublishedService(),
    ITEM_CORRECT: EnqueueCorrectedService(),
    ITEM_KILL: EnqueueKilledService()
}


def get_enqueue_service(operation):
    return enqueue_services[operation]


class EnqueueContent(superdesk.Command):
    """Runs deliveries"""

    def run(self):
        """Fetches items from publish queue as per the configuration, calls the transmit function.
        """
        lock_name = get_lock_id('publish', 'enqueue_published')
        if not lock(lock_name, expire=310):
            logger.info('Enqueue Task: {} is already running.'.format(lock_name))
            return

        try:
            items = get_published_items()

            if len(items) > 0:
                enqueue_items(items)
        finally:
            unlock(lock_name)


def enqueue_item(published_item):
    """
    Creates the corresponding entries in the publish queue for the given item
    """
    published_item_id = ObjectId(published_item[config.ID_FIELD])
    published_service = get_resource_service(PUBLISHED)
    archive_service = get_resource_service(ARCHIVE)
    published_update = {QUEUE_STATE: PUBLISH_STATE.IN_PROGRESS, 'last_queue_event': utcnow()}
    try:
        logger.info('Queueing item with id: {} and item_id: {}'.format(published_item_id, published_item['item_id']))

        published_item = published_service.find_one(req=None, _id=published_item_id)
        if published_item.get(QUEUE_STATE) != PUBLISH_STATE.PENDING:
            logger.info('Queue State is not pending for published item {}. It is in {}'.
                        format(published_item_id, published_item.get(QUEUE_STATE)))
            return

        if published_item.get(ITEM_STATE) == CONTENT_STATE.SCHEDULED:
            # if scheduled then change the state to published
            # change the `version` and `versioncreated` for the item
            # in archive collection and published collection.
            versioncreated = utcnow()
            item_updates = {'versioncreated': versioncreated, ITEM_STATE: CONTENT_STATE.PUBLISHED}
            resolve_document_version(document=item_updates, resource=ARCHIVE,
                                     method='PATCH',
                                     latest_doc={config.VERSION: published_item[config.VERSION]})

            # update the archive collection
            archive_item = archive_service.find_one(req=None, _id=published_item['item_id'])
            archive_service.system_update(published_item['item_id'], item_updates, archive_item)
            # insert into version.
            insert_into_versions(published_item['item_id'], doc=None)
            # import to legal archive
            import_into_legal_archive.apply_async(countdown=3, kwargs={'item_id': published_item['item_id']})
            logger.info('Modified the version of scheduled item: {}'.format(published_item_id))

            logger.info('Publishing scheduled item_id: {}'.format(published_item_id))
            # update the published collection
            published_update.update(item_updates)
            published_item.update({'versioncreated': versioncreated,
                                   ITEM_STATE: CONTENT_STATE.PUBLISHED,
                                   config.VERSION: item_updates[config.VERSION]})
            # send a notification to the clients
            push_content_notification(
                [{'_id': str(published_item['item_id']), 'task': published_item.get('task', None)}])

        published_service.patch(published_item_id, published_update)
        # queue the item for publishing
        queued = get_enqueue_service(published_item[ITEM_OPERATION]).enqueue_item(published_item)

        # if the item is queued in the publish_queue then the state is "queued"
        # else the queue state is "queued_not_transmitted"
        queue_state = PUBLISH_STATE.QUEUED if queued else PUBLISH_STATE.QUEUED_NOT_TRANSMITTED
        published_service.patch(published_item_id, {QUEUE_STATE: queue_state})
        logger.info('Queued item with id: {} and item_id: {}'.format(published_item_id, published_item['item_id']))
    except KeyError as key_error:
        error_updates = {QUEUE_STATE: PUBLISH_STATE.ERROR, ERROR_MESSAGE: str(key_error)}
        published_service.patch(published_item_id, error_updates)
        logger.exception('No enqueue service found for operation %s', published_item[ITEM_OPERATION])
    except ConnectionTimeout as error:  # recoverable, set state to pending and retry next time
        error_updates = {QUEUE_STATE: PUBLISH_STATE.PENDING, ERROR_MESSAGE: str(error)}
        published_service.patch(published_item_id, error_updates)
        raise
    except Exception as error:
        error_updates = {QUEUE_STATE: PUBLISH_STATE.ERROR, ERROR_MESSAGE: str(error)}
        published_service.patch(published_item_id, error_updates)
        raise


def get_published_items():
    """
    Get all items with queue state: "pending" that are not scheduled or scheduled time has lapsed.
    """
    query = {
        QUEUE_STATE: PUBLISH_STATE.PENDING,
        '$or': [
            {
                ITEM_STATE: {'$ne': CONTENT_STATE.SCHEDULED}
            },
            {
                ITEM_STATE: CONTENT_STATE.SCHEDULED,
                '{}.utc_{}'.format(SCHEDULE_SETTINGS, PUBLISH_SCHEDULE): {'$lte': utcnow()}
            }
        ]
    }
    request = ParsedRequest()
    request.sort = 'publish_sequence_no'
    request.max_results = 200
    return list(get_resource_service(PUBLISHED).get_from_mongo(req=request, lookup=query))


def enqueue_items(published_items):
    """Creates the corresponding entries in the publish queue for each item

    :param list published_items: the list of items marked for publishing
    """
    failed_items = {}

    for queue_item in published_items:
        try:
            enqueue_item(queue_item)
        except:
            logger.exception('Failed to queue item {}'.format(queue_item.get('_id')))
            failed_items[str(queue_item.get('_id'))] = queue_item

    if len(failed_items) > 0:
        logger.error('Failed to publish the following items: {}'.format(failed_items.keys()))


superdesk.command('publish:enqueue', EnqueueContent())


@celery.task(soft_time_limit=300)
def enqueue_published():
    """Pick new items from ``published`` collection and enqueue it."""
    with ProfileManager('publish:enqueue'):
        EnqueueContent().run()

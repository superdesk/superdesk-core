# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from superdesk import get_resource_service
import superdesk
from superdesk.celery_app import celery
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock
from superdesk.utc import utcnow
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, PUBLISH_SCHEDULE

from bson.objectid import ObjectId
from eve.utils import config, ParsedRequest

from apps.archive.common import ITEM_OPERATION, ARCHIVE, get_utc_schedule
from apps.publish.enqueue.enqueue_corrected import EnqueueCorrectedService
from apps.publish.enqueue.enqueue_killed import EnqueueKilledService
from apps.publish.enqueue.enqueue_published import EnqueuePublishedService
from apps.publish.published_item import PUBLISH_STATE, QUEUE_STATE, PUBLISHED
from apps.legal_archive.commands import import_into_legal_archive


logger = logging.getLogger(__name__)

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

    def run(self, provider_type=None):
        """
        Fetches items from publish queue as per the configuration,
        calls the transmit function.
        """
        lock_name = get_lock_id('publish', 'enqueue_published')
        if not lock(lock_name, '', expire=5):
            logger.info('Enqueue Task: {} is already running.'.format(lock_name))
            return

        try:
            items = get_published_items()
            logger.warning('***** ITEMS %s' % [i['_id'] for i in items])

            if len(items) > 0:
                enqueue_items(items)
        finally:
            unlock(lock_name, '')


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
        if published_item.get(ITEM_STATE) == CONTENT_STATE.SCHEDULED:
            # if scheduled then change the state to published
            logger.info('Publishing scheduled item_id: {}'.format(published_item_id))
            published_update[ITEM_STATE] = CONTENT_STATE.PUBLISHED
            archive_service.patch(published_item['item_id'], {ITEM_STATE: CONTENT_STATE.PUBLISHED})
            import_into_legal_archive.apply_async(countdown=3, kwargs={'item_id': published_item['item_id']})

        published_service.patch(published_item_id, published_update)
        get_enqueue_service(published_item[ITEM_OPERATION]).enqueue_item(published_item)
        published_service.patch(published_item_id, {QUEUE_STATE: PUBLISH_STATE.QUEUED})
        logger.info('Queued item with id: {} and item_id: {}'.format(published_item_id, published_item['item_id']))
    except KeyError:
        published_service.patch(published_item_id, {QUEUE_STATE: PUBLISH_STATE.PENDING})
        logger.exception('No enqueue service found for operation %s', published_item[ITEM_OPERATION])
    except:
        published_service.patch(published_item_id, {QUEUE_STATE: PUBLISH_STATE.PENDING})
        raise


def get_published_items():
    """
    Returns a list of items marked for publishing.
    """
    query = {QUEUE_STATE: PUBLISH_STATE.PENDING}
    request = ParsedRequest()
    request.sort = 'publish_sequence_no'
    request.max_results = 100
    return list(get_resource_service(PUBLISHED).get_from_mongo(req=request, lookup=query))


def enqueue_items(published_items):
    """
    Creates the corresponding entries in the publish queue for each item
    :param list published_items: the list of items marked for publishing
    """
    failed_items = {}
    current_utc = utcnow()

    for queue_item in published_items:
        try:
            schedule_utc_datetime = get_utc_schedule(queue_item, PUBLISH_SCHEDULE)
            if not schedule_utc_datetime or schedule_utc_datetime < current_utc:
                enqueue_item(queue_item)
        except:
            logger.exception('Failed to queue item {}'.format(queue_item.get('_id')))
            failed_items[str(queue_item.get('_id'))] = queue_item

    # mark failed items as pending so that Celery tasks will try again
    if len(failed_items) > 0:
        logger.error('Failed to publish the following items: {}'.format(failed_items.keys()))


superdesk.command('publish:enqueue', EnqueueContent())


@celery.task
def enqueue_published():
    EnqueueContent().run()

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from datetime import datetime

import superdesk
from superdesk.celery_app import celery
from superdesk.utc import utcnow
import superdesk.publish
from superdesk.errors import PublishQueueError
from superdesk.celery_task_utils import is_task_running, mark_task_as_not_running
from superdesk import get_resource_service

logger = logging.getLogger(__name__)

UPDATE_SCHEDULE_DEFAULT = {'seconds': 10}
PUBLISH_QUEUE = 'publish_queue'
STATE_PENDING = 'pending'


class PublishContent(superdesk.Command):
    """Runs deliveries"""

    def run(self, provider_type=None):
        publish.apply_async(expires=10)


@celery.task(soft_time_limit=1800)
def publish():
    """
    Fetches items from publish queue as per the configuration,
    calls the transmit function.
    """

    if is_task_running("Transmit", "Articles", UPDATE_SCHEDULE_DEFAULT):
        return

    try:
        items = get_queue_items()

        if items.count() > 0:
            transmit_items(items)
    finally:
        mark_task_as_not_running("Transmit", "Articles")


def get_queue_items():
    lookup = {'$and': [{'state': STATE_PENDING}, {'destination.delivery_type': {'$ne': 'pull'}}]}
    return get_resource_service(PUBLISH_QUEUE).get(req=None, lookup=lookup)


def transmit_items(queue_items):
    publish_queue_service = get_resource_service(PUBLISH_QUEUE)
    failed_items = {}

    for queue_item in queue_items:
        try:
            if not is_on_time(queue_item):
                continue

            # update the status of the item to in-progress
            queue_update = {'state': 'in-progress', 'transmit_started_at': utcnow()}
            publish_queue_service.patch(queue_item.get('_id'), queue_update)

            destination = queue_item['destination']

            transmitter = superdesk.publish.registered_transmitters[destination.get('delivery_type')]
            transmitter.transmit(queue_item)
            update_content_state(queue_item)
        except Exception as ex:
            logger.exception(ex)
            failed_items[str(queue_item.get('_id'))] = queue_item

    # mark failed items as pending so that Celery tasks will try again
    if len(failed_items) > 0:
        for item_id in failed_items.keys():
            try:
                orig_item = publish_queue_service.find_one(item_id)
                publish_queue_service.system_update(
                    item_id, {'state': STATE_PENDING}, orig_item)
            except:
                logger.error(
                    'Failed to set the publish queue item back to "pending" '
                    'state: {}'.format(item_id))

        logger.error('Failed to publish the following items: {}'.format(failed_items.keys()))


def is_on_time(queue_item):
    """
    Checks if the item is ready to be processed

    :param queue_item: item to be checked
    :return: True if the item is ready
    """

    try:
        if queue_item.get('publish_schedule'):
            publish_schedule = queue_item['publish_schedule']
            if type(publish_schedule) is not datetime:
                raise PublishQueueError.bad_schedule_error(Exception("Schedule is not datetime"), queue_item['_id'])
            return utcnow() >= publish_schedule

        return True
    except PublishQueueError:
        raise
    except Exception as ex:
        raise PublishQueueError.bad_schedule_error(ex, queue_item['destination'])


def update_content_state(queue_item):
    """
    Updates the state of the content item to published, in archive and published collections.
    """

    if queue_item.get('publish_schedule'):
        try:
            item_update = {'state': 'published'}
            get_resource_service('archive').patch(queue_item['item_id'], item_update)
            get_resource_service('published').update_published_items(queue_item['item_id'], 'state', 'published')
        except Exception as ex:
            raise PublishQueueError.content_update_error(ex)

superdesk.command('publish:transmit', PublishContent())

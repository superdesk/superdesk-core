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

import superdesk
from superdesk.celery_app import celery
from superdesk.utc import utcnow
import superdesk.publish
from eve.utils import config
from superdesk.lock import lock, unlock
from superdesk.celery_task_utils import get_lock_id
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
    lock_name = get_lock_id("Transmit", "Articles")
    if not lock(lock_name, '', expire=1800):
        logger.info('Task: {} is already running.'.format(lock_name))
        return

    try:
        items = get_queue_items()

        if items.count() > 0:
            transmit_items(items)

    except:
        logger.exception('Task: {} failed.'.format(lock_name))
    finally:
        unlock(lock_name, '')


def get_queue_items():
    lookup = {'$and': [{'state': STATE_PENDING}, {'destination.delivery_type': {'$ne': 'pull'}}]}
    return get_resource_service(PUBLISH_QUEUE).get(req=None, lookup=lookup)


def transmit_items(queue_items):
    publish_queue_service = get_resource_service(PUBLISH_QUEUE)
    failed_items = {}

    for queue_item in queue_items:
        log_msg = '_id: {_id}  item_id: {item_id}  ' \
                  'item_version: {item_version} headline: {headline}'.format(**queue_item)
        try:
            # update the status of the item to in-progress
            logger.info('Transmitting queue item {}'.format(log_msg))
            queue_update = {'state': 'in-progress', 'transmit_started_at': utcnow()}
            publish_queue_service.patch(queue_item.get(config.ID_FIELD), queue_update)
            destination = queue_item['destination']
            transmitter = superdesk.publish.registered_transmitters[destination.get('delivery_type')]
            transmitter.transmit(queue_item)
            logger.info('Transmitted queue item {}'.format(log_msg))
        except:
            logger.exception('Failed to transmit queue item {}'.format(log_msg))
            failed_items[str(queue_item.get(config.ID_FIELD))] = queue_item

    # mark failed items as pending so that Celery tasks will try again
    if len(failed_items) > 0:
        for item_id in failed_items.keys():
            try:
                orig_item = publish_queue_service.find_one(req=None, _id=item_id)
                publish_queue_service.system_update(
                    orig_item.get(config.ID_FIELD), {'state': STATE_PENDING}, orig_item)
            except:
                logger.error(
                    'Failed to set the publish queue item back to "pending" '
                    'state: {}'.format(item_id))

        logger.error('Failed to publish the following items: {}'.format(failed_items.keys()))

superdesk.command('publish:transmit', PublishContent())

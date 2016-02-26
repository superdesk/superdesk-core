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
from flask import current_app as app

from datetime import timedelta
from superdesk.celery_app import celery
from superdesk.utc import utcnow
import superdesk.publish
from eve.utils import config, ParsedRequest
from superdesk.lock import lock, unlock
from superdesk.celery_task_utils import get_lock_id
from superdesk import get_resource_service
from .publish_queue import QueueState


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
        items = list(get_queue_items())

        if len(items) > 0:
            transmit_items(items)

    except:
        logger.exception('Task: {} failed.'.format(lock_name))
    finally:
        unlock(lock_name, '')


def get_queue_items():
    lookup = {
        '$and': [
            {'$or': [
                {'state': QueueState.PENDING.value},
                {'state': QueueState.RETRYING.value, 'next_retry_attempt_at': {'$lte': utcnow()}}
            ]},
            {'destination.delivery_type': {'$ne': 'pull'}}
        ]
    }
    request = ParsedRequest()
    request.max_results = app.config.get('MAX_TRANSMIT_QUERY_LIMIT', 500)
    return get_resource_service(PUBLISH_QUEUE).get(req=request, lookup=lookup)


def transmit_items(queue_items):
    publish_queue_service = get_resource_service(PUBLISH_QUEUE)
    failed_items = {}

    for queue_item in queue_items:
        log_msg = '_id: {_id}  item_id: {item_id}  state: {state} ' \
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

    if len(failed_items) > 0:
        # failed items will retry based on MAX_TRANSMIT_RETRY_ATTEMPT
        max_retry_attempt = app.config.get('MAX_TRANSMIT_RETRY_ATTEMPT')
        retry_attempt_delay = app.config.get('TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES')
        for item_id in failed_items.keys():
            try:
                orig_item = publish_queue_service.find_one(req=None, _id=item_id)
                updates = {config.LAST_UPDATED: utcnow()}
                if orig_item.get('retry_attempt', 0) < max_retry_attempt:
                    updates['retry_attempt'] = orig_item.get('retry_attempt', 0) + 1
                    updates['state'] = QueueState.RETRYING.value
                    updates['next_retry_attempt_at'] = utcnow() + timedelta(minutes=retry_attempt_delay)
                else:
                    # all retry attempts exhausted marking the item as failed.
                    updates['state'] = QueueState.FAILED.value

                publish_queue_service.system_update(orig_item.get(config.ID_FIELD), updates, orig_item)
            except:
                logger.error('Failed to set the state for failed publish queue item {}.'.format(item_id))

        logger.error('Failed to publish the following items: {}'.format(failed_items.keys()))


def can_transmit_queue_item(queue_item):
    """
    Check if the queue item can be tranmitted or not
    :param dict queue_item: queue item
    :return boolean: True or False
    """
    if queue_item.get('state') == QueueState.RETRYING:
        if not queue_item.get('next_retry_attempt_at') <= utcnow():
            return False

    return True


superdesk.command('publish:transmit', PublishContent())

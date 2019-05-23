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
import superdesk.publish

from datetime import timedelta
from eve.utils import config, ParsedRequest
from flask import current_app as app
from superdesk import get_resource_service
from superdesk.celery_task_utils import get_lock_id
from superdesk.errors import PublishHTTPPushClientError
from superdesk.lock import lock, unlock
from superdesk.celery_app import celery
from superdesk.utc import utcnow
from superdesk.profiling import ProfileManager
from .publish_queue import QueueState
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)

UPDATE_SCHEDULE_DEFAULT = {'seconds': 10}
PUBLISH_QUEUE = 'publish_queue'
STATE_PENDING = 'pending'


class PublishContent(superdesk.Command):
    """Deliver items from ``publish_queue to destinations.``

    Example:
    ::

        $ python manage.py publish:transmit
    """

    def run(self, provider_type=None):
        publish.apply_async(expires=10)


@celery.task(soft_time_limit=1800)
def publish():
    """Fetch items from publish queue as per the configuration, call the transmit function."""
    with ProfileManager('publish:transmit'):
        lock_name = get_lock_id("Transmit", "Articles")
        if not lock(lock_name, expire=1810):
            logger.info('Task: {} is already running.'.format(lock_name))
            return

        try:
            for retries in [False, True]:  # first publish pending, retries after
                subs = get_queue_subscribers(retries=retries)
                for sub in subs:
                    transmit_subscriber_items.delay(str(sub), retries=retries)
        except Exception:
            logger.exception('Task: {} failed.'.format(lock_name))
        finally:
            unlock(lock_name)


def _get_queue_lookup(retries=False):
    if retries:
        return {
            '$and': [
                {'state': QueueState.RETRYING.value},
                {'next_retry_attempt_at': {'$lte': utcnow()}}
            ]
        }
    return {
        '$and': [
            {'state': QueueState.PENDING.value}
        ]
    }


def get_queue_subscribers(retries=False):
    lookup = _get_queue_lookup(retries)
    return app.data.mongo.pymongo(resource=PUBLISH_QUEUE).db[PUBLISH_QUEUE].distinct('subscriber_id', lookup)


def get_queue_items(retries=False, subscriber_id=None):
    lookup = _get_queue_lookup(retries)
    if subscriber_id:
        lookup['$and'].append({'subscriber_id': subscriber_id})
    request = ParsedRequest()
    request.max_results = app.config.get('MAX_TRANSMIT_QUERY_LIMIT', 100)  # limit per subscriber now
    request.sort = '[("_created", 1), ("published_seq_num", 1)]'
    return get_resource_service(PUBLISH_QUEUE).get(req=request, lookup=lookup)


@celery.task(soft_time_limit=600)
def transmit_subscriber_items(subscriber, retries=False):
    lock_name = get_lock_id('Subscriber', 'Transmit', subscriber)
    is_async = get_resource_service('subscribers').is_async(subscriber)

    if not lock(lock_name, expire=610):
        return

    try:
        queue_items = get_queue_items(retries, subscriber)
        for queue_item in queue_items:
            args = [queue_item[config.ID_FIELD]]
            kwargs = {'is_async': is_async}
            if is_async:
                transmit_item.apply_async(args=args, kwargs=kwargs)
            else:
                transmit_item.apply(args=args, kwargs=kwargs, throw=True)
    finally:
        unlock(lock_name)


@celery.task(soft_time_limit=300)
def transmit_item(queue_item_id, is_async=False):
    publish_queue_service = get_resource_service(PUBLISH_QUEUE)
    lock_name = get_lock_id('Transmit', str(queue_item_id))
    if is_async and not lock(lock_name, expire=310):
        return
    try:
        # check the status of the queue item
        queue_item = publish_queue_service.find_one(req=None, _id=queue_item_id)
        if queue_item.get('state') not in [QueueState.PENDING.value, QueueState.RETRYING.value]:
            logger.info('Transmit State is not pending/retrying for queue item: {}. It is in {}'.
                        format(queue_item.get(config.ID_FIELD), queue_item.get('state')))
            return

        log_msg = '_id: {_id}  item_id: {item_id}  state: {state} ' \
                  'item_version: {item_version} headline: {headline}'.format(**queue_item)

        # update the status of the item to in-progress
        queue_update = {'state': 'in-progress', 'transmit_started_at': utcnow()}
        publish_queue_service.patch(queue_item.get(config.ID_FIELD), queue_update)
        logger.info('Transmitting queue item {}'.format(log_msg))

        destination = queue_item['destination']
        transmitter = superdesk.publish.registered_transmitters[destination.get('delivery_type')]
        transmitter.transmit(queue_item)
        logger.info('Transmitted queue item {}'.format(log_msg))
    except Exception as e:
        logger.exception('Failed to transmit queue item {}'.format(log_msg))

        max_retry_attempt = app.config.get('MAX_TRANSMIT_RETRY_ATTEMPT')
        retry_attempt_delay = app.config.get('TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES')
        try:
            orig_item = publish_queue_service.find_one(req=None, _id=queue_item['_id'])
            updates = {config.LAST_UPDATED: utcnow()}

            if orig_item.get('retry_attempt', 0) < max_retry_attempt and \
                    not isinstance(e, PublishHTTPPushClientError):

                updates['retry_attempt'] = orig_item.get('retry_attempt', 0) + 1
                updates['state'] = QueueState.RETRYING.value
                updates['next_retry_attempt_at'] = utcnow() + timedelta(minutes=retry_attempt_delay)
            else:
                # all retry attempts exhausted marking the item as failed.
                updates['state'] = QueueState.FAILED.value

            publish_queue_service.system_update(orig_item.get(config.ID_FIELD), updates, orig_item)
        except Exception:
            logger.error('Failed to set the state for failed publish queue item {}.'.format(queue_item['_id']))
        if isinstance(e, SoftTimeLimitExceeded):
            raise
    finally:
        if is_async:
            unlock(lock_name, remove=True)


def transmit_items(queue_items):
    # get a distinct list of the subscribers that have queued items
    subscribers = list(set([q['subscriber_id'] for q in queue_items]))
    # extract the queued items for each subscriber and transmit them
    for subscriber in subscribers:
        sub_queue_items = [item for item in queue_items if item['subscriber_id'] == subscriber]
        transmit_subscriber_items.apply_async(kwargs={'queue_items': sub_queue_items, 'subscriber': str(subscriber)})


superdesk.command('publish:transmit', PublishContent())

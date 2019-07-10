# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from eve.utils import config

from apps.archive.common import ITEM_OPERATION
from apps.publish.content.kill import ITEM_KILL
from superdesk import get_resource_service
from superdesk.metadata.item import CONTENT_STATE
from apps.publish.enqueue.enqueue_service import EnqueueService


logger = logging.getLogger(__name__)


class EnqueueKilledService(EnqueueService):

    publish_type = 'kill'
    published_state = 'killed'

    def get_subscribers(self, doc, target_media_type):
        """Get the subscribers for this document based on the target_media_type for kill.

        Kill is sent to all subscribers that have received the item previously (published or corrected)

        :param doc: Document to kill
        :param target_media_type: Valid values are - Wire, Digital.
        :return: (list, dict, dict) List of filtered subscribers, product codes per subscriber,
                associations per subscriber
        """

        query = {'$and': [{'item_id': doc['item_id']},
                          {'publishing_action': {'$in': [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]}}]}
        subscribers, subscriber_codes, associations = self._get_subscribers_for_previously_sent_items(query)

        return subscribers, subscriber_codes, associations

    def enqueue_archived_kill_item(self, item, transmission_details):
        """Enqueue items that are killed from dusty archive.

        :param dict item: item from the archived collection.
        :param list transmission_details: list of legal publish queue entries
        """
        subscriber_ids = [transmission_record['_subscriber_id'] for transmission_record in transmission_details]
        api_subscribers = {t['_subscriber_id'] for t in transmission_details if
                           t.get('destination', {}).get('delivery_type') == 'content_api'}
        query = {'$and': [{config.ID_FIELD: {'$in': subscriber_ids}}]}
        subscribers = list(get_resource_service('subscribers').get(req=None, lookup=query))

        for subscriber in subscribers:
            subscriber['api_enabled'] = subscriber.get(config.ID_FIELD) in api_subscribers

        self.queue_transmission(item, subscribers)
        logger.info('Queued Transmission for article: {}'.format(item[config.ID_FIELD]))
        self.publish_content_api(item, [subscriber for subscriber in subscribers if subscriber['api_enabled']])

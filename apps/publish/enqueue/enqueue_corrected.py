# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service
from superdesk.metadata.item import CONTENT_STATE
from eve.utils import config
from apps.publish.enqueue.enqueue_service import EnqueueService


class EnqueueCorrectedService(EnqueueService):

    publish_type = 'correct'
    published_state = 'corrected'

    def get_subscribers(self, doc, target_media_type):
        """Get the subscribers for this document based on the target_media_type for article Correction.

        1. The article is sent to Subscribers (digital and wire) who has received the article previously.
        2. Fetch Active Subscribers. After fetching exclude those who received the article previously from
           active subscribers list.
        3. If article has 'targeted_for' property then exclude subscribers of type Internet from Subscribers list.
        4. Filter the subscriber that have not received the article previously against publish filters
        and global filters for this document.

        :param doc: Document to correct
        :param target_media_type: Valid values are - Wire, Digital.
        :return: (list, dict, dict) List of filtered subscribers, product codes per subscriber,
                associations per subscriber
        """
        subscribers, subscribers_yet_to_receive = [], []

        # step 1
        query = {'$and': [{'item_id': doc['item_id']},
                          {'publishing_action': {'$in': [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]}}]}

        subscribers, subscriber_codes, previous_associations = self._get_subscribers_for_previously_sent_items(query)

        if subscribers:
            # Step 2
            query = {'is_active': True}
            active_subscribers = list(get_resource_service('subscribers').get(req=None, lookup=query))
            subscribers_yet_to_receive = [a for a in active_subscribers
                                          if not any(a[config.ID_FIELD] == s[config.ID_FIELD]
                                                     for s in subscribers)]

            if len(subscribers_yet_to_receive) > 0:
                # Step 3
                if doc.get('target_regions'):
                    subscribers_yet_to_receive = list(self.non_digital(subscribers_yet_to_receive))
                # Step 4
                subscribers_yet_to_receive, codes = \
                    self.filter_subscribers(doc, subscribers_yet_to_receive, target_media_type)
                if codes:
                    subscriber_codes.update(codes)

        subscribers = subscribers + subscribers_yet_to_receive
        associations = self._filter_subscribers_for_associations(subscribers, doc,
                                                                 target_media_type, previous_associations)

        return subscribers, subscriber_codes, associations

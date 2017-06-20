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
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, CONTENT_STATE
from eve.utils import config
from apps.publish.enqueue.enqueue_service import EnqueueService


class EnqueuePublishedService(EnqueueService):
    def get_subscribers(self, doc, target_media_type):
        """Get the subscribers for this document based on the target_media_type for publishing.

        1. Get all active subscribers.
        2. Filter the subscriber list based on the publish filter and global filters (if configured).
            a. Rewrites are sent to subscribers that received the original item or the previous rewrite.

        :param dict doc: Document to publish/correct/kill
        :param str target_media_type: Valid values are - Wire, Digital.
        :return: (list, dict, dict) List of filtered subscribers, product codes per subscriber,
                associations per subscriber
        """
        subscribers, rewrite_subscribers = [], []
        subscriber_codes, codes, rewrite_codes = {}, {}, {}
        associations, rewrite_associations = {}, {}

        rewrite_of = doc.get('rewrite_of')

        # Step 1
        query = {'is_active': True}
        subscribers = list(get_resource_service('subscribers').get(req=None, lookup=query))

        # Step 2b
        if doc.get(ITEM_TYPE) in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            if rewrite_of:
                item_ids = [rewrite_of]

                query = {'$and': [{'item_id': {'$in': item_ids}},
                                  {'publishing_action': {'$in': [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]}}]}

                rewrite_subscribers, rewrite_codes, rewrite_associations = \
                    self._get_subscribers_for_previously_sent_items(query)

        # Step 2
        subscribers, codes = self.filter_subscribers(doc, subscribers, target_media_type)

        if rewrite_subscribers:
            subscribers_ids = set(s[config.ID_FIELD] for s in rewrite_subscribers)
            subscribers = rewrite_subscribers + [s for s in subscribers if s[config.ID_FIELD] not in subscribers_ids]

        if rewrite_codes:
            # join the codes
            subscriber_codes.update(rewrite_codes)

        if codes:
            # join the codes
            subscriber_codes.update(codes)

        # update associations
        self._update_associations(associations, rewrite_associations)

        # handle associations
        associations = self._filter_subscribers_for_associations(subscribers, doc,
                                                                 target_media_type, associations)

        return subscribers, subscriber_codes, associations

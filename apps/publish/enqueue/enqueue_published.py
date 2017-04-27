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
from superdesk.metadata.packages import PACKAGE_TYPE, TAKES_PACKAGE
from superdesk.metadata.utils import is_takes_package
from eve.utils import config
from apps.publish.enqueue.enqueue_service import EnqueueService


class EnqueuePublishedService(EnqueueService):
    def get_subscribers(self, doc, target_media_type):
        """Get the subscribers for this document based on the target_media_type for publishing.

        1. Get all active subscribers.
            a. Get the list of takes subscribers if Takes Package
        2. If takes package then subsequent takes are sent to same wire subscriber as first take.
        3. Filter the subscriber list based on the publish filter and global filters (if configured).
            a. Publish to takes package subscribers if the takes package is received by the subscriber.
            b. Rewrites are sent to subscribers that received the original item or the previous rewrite.

        :param dict doc: Document to publish/correct/kill
        :param str target_media_type: dictate if the doc being queued is a Takes Package or an Individual Article.
                Valid values are - Wire, Digital. If Digital then the doc being queued is a Takes Package and if Wire
                then the doc being queues is an Individual Article.
        :return: (list, dict, dict) List of filtered subscribers, product codes per subscriber,
                associations per subscriber
        """
        subscribers, takes_subscribers, rewrite_subscribers = [], [], []
        subscriber_codes, take_codes, codes, rewrite_codes = {}, {}, {}, {}
        associations, takes_associations, rewrite_associations = {}, {}, {}
        first_take = None

        # Step 3b
        rewrite_of = doc.get('rewrite_of')
        rewrite_take_package = None
        if rewrite_of:
            rewrite_of_item = get_resource_service('archive').find_one(req=None, _id=rewrite_of)
            if rewrite_of_item:
                if is_takes_package(rewrite_of_item):
                    rewrite_take_package = rewrite_of_item
                else:
                    rewrite_take_package = self.takes_package_service.get_take_package(rewrite_of_item)

        # Step 1
        query = {'is_active': True}
        subscribers = list(get_resource_service('subscribers').get(req=None, lookup=query))

        if doc.get(ITEM_TYPE) in [CONTENT_TYPE.COMPOSITE] and doc.get(PACKAGE_TYPE) == TAKES_PACKAGE:
            # Step 1a
            query = {'$and': [{'item_id': doc['item_id']},
                              {'publishing_action': {'$in': [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]}}]}
            takes_subscribers, take_codes, takes_associations = self._get_subscribers_for_previously_sent_items(query)

            if rewrite_of and rewrite_take_package:
                # Step 3b
                query = {'$and': [{'item_id': rewrite_take_package.get(config.ID_FIELD)},
                                  {'publishing_action': {'$in': [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]}}]}
                rewrite_subscribers, rewrite_codes, rewrite_associations = \
                    self._get_subscribers_for_previously_sent_items(query)

        # Step 2
        if doc.get(ITEM_TYPE) in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            # get first take
            first_take = self.takes_package_service.get_take_by_take_no(doc, 1)
            if str(doc['item_id']) == str(first_take):
                # if the current document is the first take then continue
                first_take = None

            if first_take:
                # if first take is published then subsequent takes should to same subscribers.
                query = {'$and': [{'item_id': first_take},
                                  {'publishing_action': {'$in': [CONTENT_STATE.PUBLISHED]}}]}
                subscribers, subscriber_codes, takes_associations = \
                    self._get_subscribers_for_previously_sent_items(query)

            if rewrite_of:
                # Step 3b
                if rewrite_take_package and rewrite_take_package.get(config.ID_FIELD) == rewrite_of:
                    item_ids = self.package_service.get_residrefs(rewrite_take_package)
                else:
                    item_ids = [rewrite_of]

                query = {'$and': [{'item_id': {'$in': item_ids}},
                                  {'publishing_action': {'$in': [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]}}]}
                rewrite_subscribers, rewrite_codes, rewrite_associations = \
                    self._get_subscribers_for_previously_sent_items(query)

        # Step 3
        if not first_take:
            subscribers, codes = self.filter_subscribers(doc, subscribers, target_media_type)

        if takes_subscribers:
            # Step 3a
            subscribers_ids = set(s[config.ID_FIELD] for s in takes_subscribers)
            subscribers = takes_subscribers + [s for s in subscribers if s[config.ID_FIELD] not in subscribers_ids]

        if rewrite_subscribers:
            # Step 3b
            subscribers_ids = set(s[config.ID_FIELD] for s in rewrite_subscribers)
            subscribers = rewrite_subscribers + [s for s in subscribers if s[config.ID_FIELD] not in subscribers_ids]

        if take_codes:
            # join the codes
            subscriber_codes.update(take_codes)

        if rewrite_codes:
            # join the codes
            subscriber_codes.update(rewrite_codes)

        if codes:
            # join the codes
            subscriber_codes.update(codes)

        # update associations
        self._update_associations(associations, rewrite_associations)
        self._update_associations(associations, takes_associations)

        # handle associations
        associations = self._filter_subscribers_for_associations(subscribers, doc,
                                                                 target_media_type, associations)

        return subscribers, subscriber_codes, associations

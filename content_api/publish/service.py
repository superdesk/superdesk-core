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

from copy import copy
from eve.utils import config, ParsedRequest

from superdesk.utc import utcnow
from superdesk.services import BaseService
from superdesk.publish.formatters.ninjs_formatter import NINJSFormatter
from superdesk import get_resource_service

logger = logging.getLogger('superdesk')


class PublishService(BaseService):
    """A service for publishing to the content api.

    Serves mainly as a proxy to the data layer.
    """

    formatter = NINJSFormatter()
    subscriber = {'config': {}}

    def publish(self, item, subscribers=[]):
        """Publish an item to content api.

        This must be enabled via ``PUBLISH_TO_CONTENT_API`` setting.

        :param item: item to publish
        """

        if not self._filter_item(item):
            doc = self.formatter._transform_to_ninjs(item, self.subscriber)
            now = utcnow()
            doc.setdefault('firstcreated', now)
            doc.setdefault('versioncreated', now)
            doc['subscribers'] = [str(sub['_id']) for sub in subscribers]
            logger.info('publishing %s to %s' % (doc['guid'], subscribers))
            return self._create_doc(doc)
        else:
            return None

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            ids.extend(self._create_doc(doc, **kwargs))
        return ids

    def _create_doc(self, doc, **kwargs):
        """Create a new item or update existing."""
        item = copy(doc)
        item.setdefault('_id', item.get('guid'))
        _id = item[config.ID_FIELD] = item.pop('guid')
        original = self.find_one(req=None, _id=_id)
        if original:
            self.update(_id, item, original)
            return _id
        else:
            return super().create([item], **kwargs)[0]

    def _filter_item(self, item):
        """
        Filter the item out if it matches any API Block filter conditions
        :param item:
        :return: True of the item is blocked, False if it is OK to publish it on the API.
        """
        # Get the API blocking Filters
        req = ParsedRequest()
        filter_conditions = list(get_resource_service('content_filters').get(req=req, lookup={'api_block': True}))

        # No API blocking filters
        if not filter_conditions:
            return False

        filter_service = get_resource_service('content_filters')
        for fc in filter_conditions:
            if filter_service.does_match(fc, item):
                logger.info('API Filter block {} matched for item {}.'.format(fc, item.get(config.ID_FIELD)))
                return True

        return False

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.services import BaseService
from eve_elastic.elastic import ElasticCursor


class AnalyticsService(BaseService):
    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource, backend)
        self.provider = None

    def get(self, req, lookup):
        if 'item_id' not in lookup:
            raise SuperdeskApiError.badRequestError('The item identifier is required')
        item = get_resource_service('archive_autosave').find_one(req=None, _id=lookup['item_id'])
        if not item:
            item = get_resource_service('archive').find_one(req=None, _id=lookup['item_id'])
            if not item:
                raise SuperdeskApiError.notFoundError('Invalid item identifer')

        keywords = self.provider.get_keywords(self._transform(item))
        if not keywords:
            return ElasticCursor([])
        search_query = []
        for kwd in keywords:
            search_query.append({'term': {'_all': {'value': kwd['text'], 'boost': 10*float(kwd['relevance'])}}})
        query = {'query': {'bool': {'should': search_query}}}
        return get_resource_service('search').get(req=None, lookup=query)

    def _transform(self, item):
        text = ''
        fields = ['slugline', 'headline', 'body_html', 'body_text']
        for field in fields:
            if field in item:
                text = '{0}\n\n{1}'.format(text, item[field])
        return text

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from content_api import MONGO_PREFIX, ELASTIC_PREFIX
from content_api.items.resource import schema


class SearchResource(Resource):

    item_url = 'regex("[\w,.:-]+")'
    schema = schema

    datasource = {
        'search_backend': 'elastic',
        'source': 'items',
        'elastic_filter': {"bool": {"must_not": {"term": {"type": "composite"}}}},
        'default_sort': [('_updated', -1)],
        'aggregations': {
            'type': {'terms': {'field': 'type'}},
            'category': {'terms': {'field': 'service.name', 'size': 100}},
            'source': {'terms': {'field': 'source', 'size': 100}},
            'urgency': {'terms': {'field': 'urgency'}},
            'priority': {'terms': {'field': 'priority'}},
            'genre': {'terms': {'field': 'genre.name', 'size': 100}},
        }
    }

    item_methods = ['GET']
    resource_methods = ['GET']
    mongo_prefix = MONGO_PREFIX
    elastic_prefix = ELASTIC_PREFIX
    privileges = {'GET': 'search_capi'}

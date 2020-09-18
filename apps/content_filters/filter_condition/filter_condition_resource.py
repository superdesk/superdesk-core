# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import copy
from superdesk import get_resource_service, config, app
from superdesk.resource import Resource


default_allowed_filters = ['anpa_category',
                           'urgency',
                           'keywords',
                           'priority',
                           'slugline',
                           'type',
                           'source',
                           'headline',
                           'ednote',
                           'body_html',
                           'genre',
                           'subject',
                           'desk',
                           'stage',
                           'sms',
                           'place',
                           'ingest_provider',
                           'embargo',
                           'featuremedia',
                           'anpa_take_key',
                           'agendas']


class FilterConditionResource(Resource):
    schema = {
        'name': {
            'type': 'string',
            'required': True,
            'nullable': False,
            'empty': False,
            'iunique': True
        },
        'field': {
            'type': 'string',
            'empty': False,
            'nullable': False,
            'allowed': default_allowed_filters,
        },
        'operator': {
            'type': 'string',
            'allowed': ['in',
                        'nin',
                        'like',
                        'notlike',
                        'startswith',
                        'endswith',
                        'match',
                        'eq',
                        'ne',
                        'lt',
                        'lte',
                        'gt',
                        'gte',
                        'exists'],
            'empty': False,
            'nullable': False,
        },
        'value': {
            'type': 'string',
            'empty': False,
            'nullable': False,
        }
    }

    additional_lookup = {
        'url': 'regex("[\w,.:-]+")',
        'field': 'name'
    }

    privileges = {'POST': 'content_filters',
                  'PATCH': 'content_filters',
                  'DELETE': 'content_filters'}

    mongo_indexes = {
        'name_1': ([('name', 1)], {'unique': True}),
    }

    def pre_request_post(self, request):
        self._init_allowed_filters()

    def pre_request_patch(self, request, lookup):
        self._init_allowed_filters()

    def _init_allowed_filters(self):
        self.schema['field']['allowed'] = copy.copy(default_allowed_filters)
        self.schema['field']['allowed'].extend(app.config.get('EXCLUDED_VOCABULARY_FIELDS', []))
        lookup = {'_id': {'$nin': self.schema['field']['allowed']}, 'type': 'manageable'}
        for vocabulary in get_resource_service('vocabularies').get(req=None, lookup=lookup):
            self.schema['field']['allowed'].append(vocabulary[config.ID_FIELD])

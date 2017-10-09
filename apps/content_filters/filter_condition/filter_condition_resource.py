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
from superdesk import get_resource_service, config


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
            'allowed': ['anpa_category',
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
                        'embargo'],
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
                        'gte'],
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

    def on_init(self):
        for vocabulary in get_resource_service('vocabularies').get(req=None, lookup={}):
            self.schema['field']['allowed'].append(vocabulary[config.ID_FIELD])

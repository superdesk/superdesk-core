# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.utils import ListCursor
from superdesk import get_resource_service, config, app
from superdesk.io.subjectcodes import get_subjectcodeitems
from eve.utils import ParsedRequest
import copy


class FilterConditionParametersResource(Resource):
    url = "filter_conditions/parameters"
    resource_methods = ['GET']
    item_methods = []


class FilterConditionParametersService(BaseService):
    def get(self, req, lookup):
        values = self._get_field_values()
        fields = [{'field': 'anpa_category',
                   'operators': ['in', 'nin'],
                   'values': values['anpa_category'],
                   'value_field': 'qcode'
                   },
                  {'field': 'urgency',
                   'operators': ['in', 'nin', 'eq', 'ne', 'lt', 'lte', 'gt', 'gte'],
                   'values': values['urgency'],
                   'value_field': 'qcode'
                   },
                  {'field': 'genre',
                   'operators': ['in', 'nin'],
                   'values': values['genre'],
                   'value_field': 'qcode'
                   },
                  {'field': 'subject',
                   'operators': ['in', 'nin'],
                   'values': values['subject'],
                   'value_field': 'qcode'
                   },
                  {'field': 'priority',
                   'operators': ['in', 'nin', 'eq', 'ne', 'lt', 'lte', 'gt', 'gte'],
                   'values': values['priority'],
                   'value_field': 'qcode'
                   },
                  {'field': 'keywords',
                   'operators': ['in', 'nin']
                   },
                  {'field': 'slugline',
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'type',
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values['type'],
                   'value_field': 'qcode'
                   },
                  {'field': 'source',
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'headline',
                   'operators': ['in', 'nin', 'eq', 'ne', 'eq',
                                 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'ednote',
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'body_html',
                   'operators': ['in', 'nin', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'desk',
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values['desk'],
                   'value_field': '_id'
                   },
                  {'field': 'stage',
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values['stage'],
                   'value_field': '_id'
                   },
                  {'field': 'sms',
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values['sms'],
                   'value_field': 'name'
                   },
                  {'field': 'place',
                   'operators': ['match'],
                   'values': values['place'],
                   'value_field': 'qcode'
                   },
                  {'field': 'ingest_provider',
                   'operators': ['eq', 'ne'],
                   'values': values['ingest_provider'],
                   'value_field': '_id'
                   },
                  {'field': 'embargo',
                   'operators': ['eq', 'ne'],
                   'values': values['embargo'],
                   'value_field': 'name'
                   }]
        fields.extend(self._get_vocabulary_fields(values))
        return ListCursor(fields)

    def _get_vocabulary_fields(self, values):
        excluded_vocabularies = copy.copy(app.config.get('EXCLUDED_VOCABULARY_FIELDS', []))
        excluded_vocabularies.extend(values)
        lookup = {'_id': {'$nin': excluded_vocabularies}, 'type': 'manageable'}
        for vocabulary in get_resource_service('vocabularies').get(req=None, lookup=lookup):
            field = {'field': vocabulary[config.ID_FIELD], 'label': vocabulary['display_name']}
            if vocabulary.get('field_type', '') == 'text':
                field['operators'] = ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
            else:
                field['values'] = vocabulary['items']
                field['operators'] = ['in', 'nin']
                field['value_field'] = 'qcode'
            yield field

    def _get_field_values(self):
        values = {}
        vocabularies_resource = get_resource_service('vocabularies')
        values['anpa_category'] = vocabularies_resource.find_one(req=None, _id='categories')['items']
        req = ParsedRequest()
        req.where = json.dumps({'$or': [{"schema_field": "genre"}, {"_id": "genre"}]})
        genre = vocabularies_resource.get(req=req, lookup=None)
        if genre.count():
            values['genre'] = genre[0]['items']
        values['urgency'] = vocabularies_resource.find_one(req=None, _id='urgency')['items']
        values['priority'] = vocabularies_resource.find_one(req=None, _id='priority')['items']
        values['type'] = vocabularies_resource.find_one(req=None, _id='type')['items']
        subject = vocabularies_resource.find_one(req=None, schema_field='subject')
        if subject:
            values['subject'] = subject['items']
        else:
            values['subject'] = get_subjectcodeitems()
        values['desk'] = list(get_resource_service('desks').get(None, {}))
        values['stage'] = self._get_stage_field_values(values['desk'])
        values['sms'] = [{'qcode': 0, 'name': 'False'}, {'qcode': 1, 'name': 'True'}]
        values['embargo'] = [{'qcode': 0, 'name': 'False'}, {'qcode': 1, 'name': 'True'}]
        req = ParsedRequest()
        req.where = json.dumps({'$or': [{"schema_field": "place"}, {"_id": "place"}, {"_id": "locators"}]})
        place = vocabularies_resource.get(req=req, lookup=None)
        if place.count():
            values['place'] = place[0]['items']
        values['ingest_provider'] = list(get_resource_service('ingest_providers').get(None, {}))
        return values

    def _get_stage_field_values(self, desks):
        stages = list(get_resource_service('stages').get(None, {}))
        for stage in stages:
            desk = next(filter(lambda d: d['_id'] == stage['desk'], desks))
            stage['name'] = '{}: {}'.format(desk['name'], stage['name'])
        return stages

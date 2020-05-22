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
import copy
import logging
from flask_babel import _
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.utils import ListCursor
from superdesk import get_resource_service, config, app
from superdesk.io.subjectcodes import get_subjectcodeitems
from eve.utils import ParsedRequest


logger = logging.getLogger(__name__)


class FilterConditionParametersResource(Resource):
    url = "filter_conditions/parameters"
    resource_methods = ['GET']
    item_methods = []
    schema = {
        'field': {'type': 'string'},
        'label': {'type': 'string'},
        'operators': {'type': 'list'},
        'values': {'type': 'list'},
        'value_field': {'type': 'string'},
    }


class FilterConditionParametersService(BaseService):
    def get(self, req, lookup):
        values = self._get_field_values()
        fields = [{'field': 'anpa_category',
                   'label': _('ANPA Category'),
                   'operators': ['in', 'nin'],
                   'values': values.get('anpa_category', []),
                   'value_field': 'qcode'
                   },
                  {'field': 'urgency',
                   'label': _('Urgency'),
                   'operators': ['in', 'nin', 'eq', 'ne', 'lt', 'lte', 'gt', 'gte'],
                   'values': values.get('urgency', []),
                   'value_field': 'qcode'
                   },
                  {'field': 'genre',
                   'label': _('Genre'),
                   'operators': ['in', 'nin'],
                   'values': values.get('genre', []),
                   'value_field': 'qcode'
                   },
                  {'field': 'subject',
                   'label': _('Subject'),
                   'operators': ['in', 'nin'],
                   'values': values.get('subject', []),
                   'value_field': 'qcode'
                   },
                  {'field': 'priority',
                   'label': _('Priority'),
                   'operators': ['in', 'nin', 'eq', 'ne', 'lt', 'lte', 'gt', 'gte'],
                   'values': values.get('priority', []),
                   'value_field': 'qcode'
                   },
                  {'field': 'keywords',
                   'label': _('Keywords'),
                   'operators': ['in', 'nin']
                   },
                  {'field': 'slugline',
                   'label': _('Slugline'),
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'type',
                   'label': _('Type'),
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values.get('type', []),
                   'value_field': 'qcode'
                   },
                  {'field': 'source',
                   'label': _('Source'),
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'headline',
                   'label': _('Headline'),
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'ednote',
                   'label': _('Ednote'),
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'body_html',
                   'label': _('Body HTML'),
                   'operators': ['in', 'nin', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  {'field': 'desk',
                   'label': _('Desk'),
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values['desk'],
                   'value_field': '_id'
                   },
                  {'field': 'stage',
                   'label': _('Stage'),
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values['stage'],
                   'value_field': '_id'
                   },
                  {'field': 'sms',
                   'label': _('SMS'),
                   'operators': ['in', 'nin', 'eq', 'ne'],
                   'values': values['sms'],
                   'value_field': 'name'
                   },
                  {'field': 'place',
                   'label': _('Place'),
                   'operators': ['match', 'in', 'nin'],
                   'values': values['place'],
                   'value_field': 'qcode'
                   },
                  {'field': 'ingest_provider',
                   'label': _('Ingest provider'),
                   'operators': ['eq', 'ne'],
                   'values': values['ingest_provider'],
                   'value_field': '_id'
                   },
                  {'field': 'embargo',
                   'label': _('Embargo'),
                   'operators': ['eq', 'ne'],
                   'values': values['embargo'],
                   'value_field': 'name'
                   },
                  {'field': 'featuremedia',
                   'label': _('Feature Media'),
                   'operators': ['exists'],
                   'values': values['featuremedia'],
                   'value_field': 'name'
                   },
                  {'field': 'anpa_take_key',
                   'operators': ['in', 'nin', 'eq', 'ne', 'like', 'notlike', 'startswith', 'endswith']
                   },
                  ]

        if 'planning' in app.config.get('INSTALLED_APPS', []):
            fields.append({'field': 'agendas',
                           'label': _('Agendas'),
                           'operators': ['in', 'nin'],
                           'values': list(get_resource_service('agenda').find({'is_enabled': True})),
                           'value_field': '_id',
                           })

        fields.extend(self._get_vocabulary_fields(values))
        return ListCursor(fields)

    def _get_vocabulary_fields(self, values):
        excluded_vocabularies = copy.copy(app.config.get('EXCLUDED_VOCABULARY_FIELDS', []))
        excluded_vocabularies.extend(values)
        lookup = {'_id': {'$nin': excluded_vocabularies}, 'type': 'manageable'}
        for vocabulary in get_resource_service('vocabularies').get(req=None, lookup=lookup):
            field = {'field': vocabulary[config.ID_FIELD], 'label': vocabulary['display_name']}

            if vocabulary.get('field_type') and vocabulary.get('field_type', '') != 'text':
                continue

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
        categories_cv = vocabularies_resource.find_one(req=None, _id='categories')
        values['anpa_category'] = categories_cv.get('items') if categories_cv else []
        req = ParsedRequest()
        req.where = json.dumps({'$or': [{"schema_field": "genre"}, {"_id": "genre"}]})
        genre = vocabularies_resource.get(req=req, lookup=None)
        if genre.count():
            values['genre'] = genre[0]['items']
        for voc_id in ('urgency', 'priority', 'type'):
            try:
                values[voc_id] = vocabularies_resource.find_one(req=None, _id=voc_id)['items']
            except TypeError:
                values[voc_id] = []
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
        else:
            values['place'] = []
        values['ingest_provider'] = list(get_resource_service('ingest_providers').get(None, {}))
        values['featuremedia'] = [{'qcode': 1, 'name': 'True'}, {'qcode': 0, 'name': 'False'}]
        return values

    def _get_stage_field_values(self, desks):
        stages = list(get_resource_service('stages').get(None, {}))
        for i, stage in enumerate(stages):
            try:
                desk = next(filter(lambda d: d['_id'] == stage['desk'], desks))
            except StopIteration:
                # if stage has no desk, remove that stage from a list
                logger.warning('Desk not found for stage with id "{}".'.format(stage['_id']))
                stages[i] = None
                continue
            stages[i]['name'] = '{}: {}'.format(desk['name'], stage['name'])
        return tuple(i for i in stages if i)

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
from superdesk import get_resource_service
from superdesk.io.subjectcodes import get_subjectcodeitems
from eve.utils import ParsedRequest


class FilterConditionParametersResource(Resource):
    url = "filter_conditions/parameters"
    resource_methods = ['GET']
    item_methods = []


class FilterConditionParametersService(BaseService):
    def get(self, req, lookup):
        values = self._get_field_values()
        return ListCursor([{'field': 'anpa_category',
                            'operators': ['in', 'nin'],
                            'values': values['anpa_category'],
                            'value_field': 'qcode'
                            },
                           {'field': 'urgency',
                            'operators': ['in', 'nin'],
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
                            'operators': ['in', 'nin'],
                            'values': values['priority'],
                            'value_field': 'qcode'
                            },
                           {'field': 'keywords',
                            'operators': ['in', 'nin']
                            },
                           {'field': 'slugline',
                            'operators': ['in', 'nin', 'like', 'notlike', 'startswith', 'endswith']
                            },
                           {'field': 'type',
                            'operators': ['in', 'nin'],
                            'values': values['type'],
                            'value_field': 'qcode'
                            },
                           {'field': 'source',
                            'operators': ['in', 'nin', 'like', 'notlike', 'startswith', 'endswith']
                            },
                           {'field': 'headline',
                            'operators': ['in', 'nin', 'like', 'notlike', 'startswith', 'endswith']
                            },
                           {'field': 'ednote',
                            'operators': ['in', 'nin', 'like', 'notlike', 'startswith', 'endswith']
                            },
                           {'field': 'body_html',
                            'operators': ['in', 'nin', 'like', 'notlike', 'startswith', 'endswith']
                            },
                           {'field': 'desk',
                            'operators': ['in', 'nin'],
                            'values': values['desk'],
                            'value_field': '_id'
                            },
                           {'field': 'stage',
                            'operators': ['in', 'nin'],
                            'values': values['stage'],
                            'value_field': '_id'
                            },
                           {'field': 'sms',
                            'operators': ['in', 'nin'],
                            'values': values['sms'],
                            'value_field': 'name'
                            }])

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
        return values

    def _get_stage_field_values(self, desks):
        stages = list(get_resource_service('stages').get(None, {}))
        for stage in stages:
            desk = next(filter(lambda d: d['_id'] == stage['desk'], desks))
            stage['name'] = '{}: {}'.format(desk['name'], stage['name'])
        return stages

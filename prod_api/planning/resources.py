# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.metadata.utils import item_url


class PlanningResource(Resource):
    url = 'planning'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'planning',
        'search_backend': 'elastic',
        'default_sort': [('_updated', -1)],
        'projection': {
            'fields_meta': 0
        },
    }


class EventsResource(Resource):
    url = 'events'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'events',
        'search_backend': 'elastic',
        'default_sort': [('dates.start', 1)],
        'projection': {
            'fields_meta': 0
        },
    }


class AssignmentsResource(Resource):
    url = 'assignments'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'assignments',
        'search_backend': 'elastic',
        'default_sort': [('_updated', -1)],
        'projection': {
            'fields_meta': 0
        },
    }

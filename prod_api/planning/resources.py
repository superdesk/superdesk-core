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
from superdesk.auth_server.scopes import Scope


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
    privileges = {
        'GET': Scope.PLANNING_READ.name
    }


class EventsResource(Resource):
    url = 'events'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'events',
        'search_backend': 'elastic',
        'default_sort': [('_updated', -1)],
        'projection': {
            'fields_meta': 0
        },
    }
    privileges = {
        'GET': Scope.EVENTS_READ.name
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
    privileges = {
        'GET': Scope.ASSIGNMENTS_READ.name
    }


class EventsHistoryResource(Resource):
    url = 'events_history'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'events_history',
        'default_sort': [('_updated', -1)],
        'projection': {
            # NOTE: since schema is not defined here, setting up a projection explicitly is required,
            # otherwise default `eve` fields (projection) will be applied e.q. `{'_id': 1}`
            # and it will cut off all required data.
            # https://github.com/pyeve/eve/blob/afd573d9254a9a23393f35760e9c515300909ccd/eve/io/base.py#L420
            '_etag': 0
        },
    }
    privileges = {
        'GET': Scope.EVENTS_READ.name
    }


class EventsFilesResource(Resource):
    url = 'events_files'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'events_files',
        'default_sort': [('_updated', -1)],
        'projection': {
            # NOTE: since schema is not defined here, setting up a projection explicitly is required,
            # otherwise default `eve` fields (projection) will be applied e.q. `{'_id': 1}`
            # and it will cut off all required data.
            # https://github.com/pyeve/eve/blob/afd573d9254a9a23393f35760e9c515300909ccd/eve/io/base.py#L420
            '_etag': 0
        },
    }
    privileges = {
        'GET': Scope.EVENTS_READ.name
    }

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.errors import SuperdeskApiError
from superdesk.services import BaseService

from superdesk.metadata.item import metadata_schema
from superdesk.resource import Resource


class SavedActivityReportResource(Resource):
    """Saved Activity Report schema
    """

    schema = {
        'name': {
            'type': 'string',
            'required': True,
            'minlength': 1
        },
        'description': {
            'type': 'string'
        },
        'is_global': {
            'type': 'boolean',
            'default': False
        },
        'owner': Resource.rel('users', nullable=True),
        'operation': {
            'type': 'string',
            'required': True
        },
        'desk': Resource.rel('desks', nullable=True),
        'operation_date': {
            'type': 'datetime',
            'required': True
        },
        'subject': metadata_schema['subject'],
        'category': metadata_schema['anpa_category'],
        'keywords': metadata_schema['keywords'],
        'urgency': metadata_schema['urgency'],
        'priority': metadata_schema['priority'],
        'subscriber': {'type': 'string'},
        'group_by': {
            'type': 'list'
        }
    }
    item_methods = ['GET', 'PATCH', 'PUT', 'DELETE']
    resource_methods = ['GET', 'POST']
    privileges = {'POST': 'activity_reports', 'PATCH': 'activity_reports',
                  'PUT': 'activity_reports', 'DELETE': 'activity_reports'}


class SavedActivityReportService(BaseService):
    """Save activity reports service
    """

    def create(self, docs, **kwargs):
        for doc in docs:
            if doc.get('group_by') and doc.get('desk'):
                raise SuperdeskApiError.badRequestError('The desk must not be defined when group by is defined.')
            if not doc.get('group_by', False) and not doc.get('desk'):
                raise SuperdeskApiError.badRequestError('The desk is required when group by desk is false')
        return super().create(docs, **kwargs)

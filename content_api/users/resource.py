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
from content_api import MONGO_PREFIX


class UsersResource(Resource):
    """
    Users schema
    """

    schema = {
        'password': {
            'type': 'string',
            'minlength': 8
        },
        'first_name': {
            'type': 'string'
        },
        'last_name': {
            'type': 'string'
        },
        'email': {
            'unique': True,
            'type': 'string',
            'required': True
        },
        'phone': {
            'type': 'string',
            'nullable': True
        },
        'signup_details': {
            'type': 'dict'
        },
        'country': {
            'type': 'string'
        },
        'company': Resource.rel('companies', embeddable=True, required=False),
        'user_type': {
            'type': 'string',
            'allowed': ['administrator', 'internal', 'public'],
            'default': 'public'
        },
        'is_validated': {
            'type': 'boolean',
            'default': False
        },
        'is_enabled': {
            'type': 'boolean',
            'default': True
        },
        'is_approved': {
            'type': 'boolean',
            'default': False
        },
        'token': {
            'type': 'string',
        },
        'token_expiry_date': {
            'type': 'datetime',
        }
    }

    item_methods = ['GET', 'PATCH', 'PUT']
    resource_methods = ['GET', 'POST']
    mongo_prefix = MONGO_PREFIX
    datasource = {
        'source': 'users',
        'projection': {'password': 0},
        'default_sort': [('name', 1)]
    }
    mongo_indexes = {
        'email': ([('email', 1)], {'unique': True})
    }

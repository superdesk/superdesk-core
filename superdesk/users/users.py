# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk Users"""

from superdesk.metadata.item import BYLINE, SIGN_OFF
from superdesk.resource import Resource


class UsersResource(Resource):

    def __init__(self, endpoint_name, app, service, endpoint_schema=None):
        self.readonly = True if app.config.get('LDAP_SERVER', None) else False

        self.additional_lookup = {
            'url': 'regex("[\w]+")',
            'field': 'username'
        }

        self.schema = {
            'username': {
                'type': 'string',
                'unique': True,
                'required': True,
                'minlength': 1
            },
            'password': {
                'type': 'string',
                'minlength': 5
            },
            'first_name': {
                'type': 'string',
                'readonly': self.readonly
            },
            'last_name': {
                'type': 'string',
                'readonly': self.readonly
            },
            'display_name': {
                'type': 'string'
            },
            'email': {
                'unique': True,
                'type': 'email',
                'required': True
            },
            'phone': {
                'type': 'string',
                'nullable': True
            },
            'language': {
                'type': 'string',
                'nullable': True
            },
            'user_info': {
                'type': 'dict'
            },
            'picture_url': {
                'type': 'string',
                'nullable': True
            },
            'avatar': Resource.rel('upload', embeddable=True, nullable=True),
            'avatar_renditions': {'type': 'dict'},
            'role': Resource.rel('roles', True),
            'privileges': {'type': 'dict'},
            'workspace': {
                'type': 'dict'
            },
            'user_type': {
                'type': 'string',
                'allowed': ['user', 'administrator'],
                'default': 'user'
            },
            'is_active': {
                'type': 'boolean',
                'default': True
            },
            'is_enabled': {
                'type': 'boolean',
                'default': True
            },
            'needs_activation': {
                'type': 'boolean',
                'default': True
            },
            'desk': Resource.rel('desks'),  # Default desk of the user, which would be selected when logged-in.
            SIGN_OFF: {  # Used for putting a sign-off on the content when it's created/updated except kill
                'type': 'string',
                'required': False,
                'regex': '^[a-zA-Z0-9]+$'
            },
            BYLINE: {
                'type': 'string',
                'required': False,
                'nullable': True
            },
            # list to hold invisible stages.
            # This field is updated under following scenario:
            # 1. stage visible flag is updated
            # 2. desk membership is modified
            # 3. new user is created
            'invisible_stages': {
                'type': 'list',
                'required': False,
                'nullable': True
            }
        }

        self.extra_response_fields = [
            'display_name',
            'username',
            'email',
            'user_info',
            'picture_url',
            'avatar',
            'is_active',
            'is_enabled',
            'needs_activation',
            'desk'
        ]

        self.etag_ignore_fields = ['session_preferences', '_etag', 'invisible_stages']

        self.datasource = {
            'projection': {'password': 0},
            'default_sort': [('username', 1)],
        }

        self.privileges = {'POST': 'users', 'DELETE': 'users', 'PATCH': 'users'}
        super().__init__(endpoint_name, app=app, service=service, endpoint_schema=endpoint_schema)

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
            'url': r'regex("[\w]+")',
            'field': 'username'
        }

        self.schema = {
            'username': {
                'type': 'string',
                'unique': True,
                'required': True,
                'minlength': 1,
                'username_pattern': True,
            },
            'password': {
                'type': 'string',
                'minlength': 5
            },
            'password_changed_on': {
                'type': 'datetime',
                'nullable': True
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
                'required': True,
                'coerce': lambda s: s.lower()
            },
            'phone': {
                'type': 'string',
                'nullable': True
            },
            'job_title': {
                'type': 'string',
                'required': False,
            },
            'biography': {
                'type': 'string',
                'required': False,
                'nullable': True,
            },
            'facebook': {
                'type': 'string',
                'required': False,
                'nullable': True,
            },
            'instagram': {
                'type': 'string',
                'required': False,
                'nullable': True,
            },
            'twitter': {
                'type': 'string',
                'required': False,
                'nullable': True,
                'twitter': True,
            },
            'jid': {
                'unique': True,
                'type': 'string',
                'required': False,
            },
            'language': {
                'type': 'string',
                'nullable': True
            },
            'user_info': {
                'type': 'dict',
                'schema': {},
                'allow_unknown': True,
            },
            'picture_url': {
                'type': 'string',
                'nullable': True
            },
            'avatar': Resource.rel('upload', embeddable=True, nullable=True),
            'avatar_renditions': {'type': 'dict', 'schema': {}},
            'role': Resource.rel('roles', True),
            'privileges': {
                'type': 'dict',
                'schema': {},
                'allow_unknown': True,
            },
            'workspace': {
                'type': 'dict',
                'schema': {},
                'allow_unknown': True,
            },
            'user_type': {
                'type': 'string',
                'allowed': ['user', 'administrator'],
                'default': 'user'
            },
            'is_support': {
                'type': 'boolean',
                'default': False
            },
            'is_author': {
                'type': 'boolean',
                'default': True
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
            # Default desk of the user, which would be selected when logged-in.
            'desk': Resource.rel('desks', nullable=True),
            SIGN_OFF: {  # Used for putting a sign-off on the content when it's created/updated except kill
                'type': 'string',
                'required': False,
                'nullable': True,
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
            },
            # If Slack notifications are configured and enabled for the user
            # the Slack username is stored here.
            'slack_username': {
                'type': 'string',
                'required': False,
                'nullable': True
            },
            # The Slack user id is stored here, to avoid repeatedly having to look it up
            'slack_user_id': {
                'type': 'string',
                'required': False,
                'nullable': True
            },
            'session_preferences': {
                'type': 'dict',
                'schema': {},
                'allow_unknown': True,
            },
            'user_preferences': {
                'type': 'dict',
                'schema': {},
                'allow_unknown': True,
            },
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

        self.mongo_indexes = {
            'username_1': ([('username', 1)], {'unique': True}),
            'first_name_1_last_name_-1': [('first_name', 1), ('last_name', -1)],
        }

        self.privileges = {'POST': 'users', 'DELETE': 'users', 'PATCH': 'users'}
        super().__init__(endpoint_name, app=app, service=service, endpoint_schema=endpoint_schema)

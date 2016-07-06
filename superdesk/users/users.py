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
    readonly = True

    additional_lookup = {
        'url': 'regex("[\w]+")',
        'field': 'username'
    }

    schema = {
        'username': {
            'type': 'string',
            'unique': True,
            'required': True,
            'minlength': 1
        },
        'password': {
            'type': 'string',
            'minlength': 5,
            'readonly': readonly
        },
        'first_name': {
            'type': 'string',
            'readonly': readonly
        },
        'last_name': {
            'type': 'string',
            'readonly': readonly
        },
        'display_name': {
            'type': 'string',
            'readonly': readonly
        },
        'email': {
            'unique': True,
            'type': 'email',
            'required': True
        },
        'phone': {
            'type': 'phone_number',
            'readonly': readonly,
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
        'role': Resource.rel('roles', True),
        'privileges': {'type': 'dict'},
        'avatar_renditions': {'type': 'dict'},
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
            'required': True,
            'regex': '^[a-zA-Z0-9]+$'
        },
        BYLINE: {
            'type': 'string',
            'required': False,
            'nullable': True
        }
    }

    extra_response_fields = [
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

    etag_ignore_fields = ['session_preferences', '_etag']

    datasource = {
        'projection': {'password': 0},
        'default_sort': [('username', 1)]
    }

    privileges = {'POST': 'users', 'DELETE': 'users', 'PATCH': 'users', 'GET': 'users'}

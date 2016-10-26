# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import jwt
import jwt.exceptions
import superdesk

from datetime import datetime, timedelta
from content_api.tokens.resource import TokensResource
from superdesk.services import BaseService
from flask import current_app as app, g
from eve.auth import TokenAuth, BasicAuth


JWT_ALGO = 'HS256'
TOKEN_TTL_DAYS = 365


def _timestamp(date=None):
    if not date:
        date = datetime.utcnow()
    return int(date.timestamp())


def _get_secret():
    return app.config['SECRET_KEY']


def generate_subscriber_token(subscriber):
    exp = datetime.utcnow() + timedelta(days=TOKEN_TTL_DAYS)
    payload = {'sub': str(subscriber['_id']), 'exp': _timestamp(exp)}
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGO)


def decode_subscriber_token(token):
    try:
        return jwt.decode(token, _get_secret(), algorithms=[JWT_ALGO])
    except jwt.exceptions.DecodeError:
        return


class SubscriberTokenAuth(TokenAuth):

    def check_auth(self, token, allowed_roles, resource, method):
        decoded = decode_subscriber_token(token)
        if not decoded:
            return
        g.user = decoded.get('sub')
        return decoded.get('sub')


def init_app(app):
    endpoint_name = 'tokens'
    service = BaseService(endpoint_name, backend=superdesk.get_backend())
    TokensResource(endpoint_name, app=app, service=service)


# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from flask import current_app as app, g
from eve.auth import TokenAuth
from superdesk.utc import utcnow
from superdesk.publish.subscriber_token import SubscriberTokenResource, SubscriberTokenService

from content_api.tokens.resource import CompanyTokenResource  # noqa
from content_api.tokens.service import CompanyTokenService  # noqa


TOKEN_RESOURCE = "subscriber_token"


class AuthSubscriberTokenResource(SubscriberTokenResource):
    item_methods = []
    resource_methods = []


class SubscriberTokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        """Try to find auth token and if valid put subscriber id into ``g.user``."""
        data = app.data.mongo.find_one(TOKEN_RESOURCE, req=None, _id=token)
        if not data:
            return False
        now = utcnow()
        if data.get("expiry") and data.get("expiry") < now:
            app.data.mongo.remove(TOKEN_RESOURCE, {"_id": token})
            return False
        g.user = str(data.get("subscriber"))
        return g.user


def init_app(app):
    superdesk.register_resource(TOKEN_RESOURCE, AuthSubscriberTokenResource, SubscriberTokenService, _app=app)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from eve.auth import BasicAuth
from flask import current_app as app
from flask import request


class BearerAuth(BasicAuth):
    """Overrides Eve's built-in basic authorization scheme and uses Redis to validate bearer token"""

    def __init__(self):
        super(BearerAuth, self).__init__()

    def check_auth(self, token, allowed_roles, resource, method):
        """Check if API request is authorized.

        Examines token in header and checks Redis cache to see if token is
        valid. If so, request is allowed.

        :param token: OAuth 2.0 access token submitted.
        :param allowed_roles: Allowed user roles.
        :param resource: Resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """
        return token and app.redis.get(token)

    def authorized(self, allowed_roles, resource, method):
        """Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        if not resource or resource in app.config['PUBLIC_RESOURCES']:
            return True
        try:
            token = request.headers.get('Authorization').split(' ')[1]
        except:
            token = None
        return self.check_auth(token, allowed_roles, resource, method)

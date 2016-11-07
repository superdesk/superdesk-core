# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask_oauthlib.provider.oauth2 import OAuth2RequestValidator
from flask_sentinel import views
from flask_sentinel.core import oauth

from content_api.auth.auth_data_manager import AuthDataManager


def get_auth_url(app):
    return '%s%s' % (app.config['OAUTH2_ROUTE_PREFIX'], app.config['OAUTH2_TOKEN_URL'])


def init_app(app):
    """Initialize the authentication endpoints.

    :param app: the API application object
    :type app: `Eve`
    """

    oauth.init_app(app)
    oauth._validator = OAuth2RequestValidator(
        clientgetter=AuthDataManager.get_client,
        tokengetter=AuthDataManager.get_token,
        usergetter=AuthDataManager.get_user,
        tokensetter=AuthDataManager.save_token,
        grantgetter=None
    )

    app.add_url_rule(get_auth_url(app), view_func=views.access_token, methods=['POST'])

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from .auth import OIDCAuthResource, OIDCAuthService


def init_app(app):
    endpoint_name = 'auth_oidc'
    app.client_config['oidc_auth'] = bool(app.config['OIDC_ENABLED']) and bool(app.config['SECRET_KEY'] != '')
    if app.client_config['oidc_auth']:
        issuer = app.config['OIDC_ISSUER']
        app.config.setdefault('OIDC_CLIENT_SECRETS', {
            "web": {
                "issuer": issuer,
                "auth_uri": issuer + '/protocol/openid-connect/auth',
                "client_id": app.config['OIDC_SERVER_CLIENT'],
                "client_secret": app.config['OIDC_SERVER_CLIENT_SECRET'],
                "userinfo_uri": issuer + '/protocol/openid-connect/userinfo',
                "token_uri": issuer + '/protocol/openid-connect/token',
                "token_introspection_uri": issuer + '/protocol/openid-connect/token/introspect'
            }
        })
        url, realm = issuer.split('/realms/')
        app.client_config['keycloak_config'] = {
            'url': url,
            'realm': realm,
            'clientId': app.config['OIDC_WEB_CLIENT'],
            'redirectUri': app.config['OIDC_BROWSER_REDIRECT_URI']
        }
        service = OIDCAuthService('auth', backend=superdesk.get_backend(), app=app)
        OIDCAuthResource(endpoint_name, app=app, service=service)

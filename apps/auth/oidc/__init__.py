# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""
Superdesk OpenID Connect Authentication

.. versionadded:: 2.1

Configuration
~~~~~~~~~~~~~

Superdesk supports OIDC authentication via Keycloak. To enable OIDC auth module, set environment variable
``OIDC_ENABLED`` to True.
Setting :ref:`settings.secret_key` is also required.

Next you need to create a server client (with **confidential**
`access type <https://www.keycloak.org/docs/latest/server_admin/#_access-type>`_) and web client (with **public**
access type). Both with ``Valid Redirect URIs`` set to :ref:`settings.default.client_url`.

Finally with your Keycloak server is running at ``localhost:8080``, ``SUPERDESK``, ``server_client``, ``web_client``
are your keycloak realm, server client, and web client respectively, set following environment variables::

    OIDC_ENABLED=True
    OIDC_ISSUER_URL=http://localhost:8080/auth/realms/SUPERDESK
    OIDC_SERVER_CLIENT=server_client
    OIDC_SERVER_CLIENT_SECRET=server-client-secret
    OIDC_WEB_CLIENT=web-client
"""
import logging

import superdesk

from .auth import OIDCAuthResource, OIDCAuthService

logger = logging.getLogger(__name__)


def init_app(app):
    endpoint_name = "auth_oidc"
    if app.config["OIDC_ENABLED"] and not app.config["SECRET_KEY"]:
        logger.warn("SECRET_KEY is not set")

    app.client_config["oidc_auth"] = app.config["OIDC_ENABLED"] and app.config["SECRET_KEY"]
    if app.client_config["oidc_auth"]:
        issuer = app.config["OIDC_ISSUER_URL"]
        app.config.setdefault(
            "OIDC_CLIENT_SECRETS",
            {
                "web": {
                    "issuer": issuer,
                    "auth_uri": issuer + "/protocol/openid-connect/auth",
                    "client_id": app.config["OIDC_SERVER_CLIENT"],
                    "client_secret": app.config["OIDC_SERVER_CLIENT_SECRET"],
                    "userinfo_uri": issuer + "/protocol/openid-connect/userinfo",
                    "token_uri": issuer + "/protocol/openid-connect/token",
                    "token_introspection_uri": issuer + "/protocol/openid-connect/token/introspect",
                }
            },
        )
        url, realm = issuer.split("/realms/")
        app.client_config["keycloak_config"] = {
            "url": url,
            "realm": realm,
            "clientId": app.config["OIDC_WEB_CLIENT"],
            "redirectUri": app.config["OIDC_BROWSER_REDIRECT_URL"],
        }
        service = OIDCAuthService("auth", backend=superdesk.get_backend(), app=app)
        OIDCAuthResource(endpoint_name, app=app, service=service)

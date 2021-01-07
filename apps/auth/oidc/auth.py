# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask import g, request
from flask_babel import _
from flask_oidc_ex import OpenIDConnect

import superdesk
from apps.auth.errors import CredentialsAuthError
from apps.auth.service import AuthService
from eve.utils import config
from superdesk import get_resource_service
from superdesk.resource import Resource
from superdesk.utils import ignorecase_query

from ..errors import CredentialsAuthError


class OIDCAuthResource(Resource):
    schema = {"token": {"type": "string"}, "user": Resource.rel("users", True)}
    resource_methods = ["POST"]
    public_methods = ["POST"]
    extra_response_fields = ["user", "token", "username"]


superdesk.intrinsic_privilege("auth_oidc", method=["DELETE"])


class OIDCAuthService(AuthService):
    def __init__(self, datasource=None, backend=None, app=None):
        super().__init__(datasource=datasource, backend=backend)
        self.oidc = OpenIDConnect(app)

    def authenticate(self, credentials):
        auth_header = request.headers.get("Authorization", "").split(" ", 1)
        if auth_header[0] != "Bearer" and len(auth_header) != 2:
            raise CredentialsAuthError(credentials)
        token = auth_header[1]
        is_valid = self.oidc.validate_token(token, ["openid", "email", "profile"])
        if not is_valid:
            raise CredentialsAuthError(credentials)

        users_service = get_resource_service("users")
        username = g.oidc_token_info["username"]
        user = users_service.find_one(req=None, username=username) or {}

        sync_data = {
            "username": username,
            "email": g.oidc_token_info.get("email", user.get("email")),
            "display_name": g.oidc_token_info.get("name"),
        }

        # first name and last name is optional in Keycloak
        if "given_name" in g.oidc_token_info:
            sync_data["first_name"] = g.oidc_token_info.get("given_name")
        if "family_name" in g.oidc_token_info:
            sync_data["last_name"] = g.oidc_token_info.get("family_name")

        if not user:
            # email is optional in Keycloak
            if not sync_data["email"]:
                raise CredentialsAuthError(sync_data, message=_("Please update your account email address"))
            user_role = None
            client_id = g.oidc_token_info.get("client_id", "")
            keycloak_roles = g.oidc_token_info.get("resource_access", {}).get(client_id, {}).get("roles", [])
            for role_name in keycloak_roles:
                role = get_resource_service("roles").find_one(req=None, name=ignorecase_query(role_name))
                if role:
                    user_role = role.get("_id")
                    break
            sync_data.update(
                {
                    "password": "",
                    "user_type": "user",
                    "role": user_role,
                    "needs_activation": False,
                }
            )
            users_service.post([sync_data])
        else:
            users_service.patch(user[config.ID_FIELD], sync_data)

        user.update(sync_data)
        return user

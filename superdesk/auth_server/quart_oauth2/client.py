# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import bcrypt
from authlib.oauth2.rfc6749 import ClientMixin


class OAuth2Client(ClientMixin):
    _id: str
    pwd_hash: str
    auth_methods: list[str]
    scope: str | None

    def __init__(self, data, auth_methods: list[str], allowed_scopes: set[str] | None = None):
        self._id = data["_id"]
        self.pwd_hash = data["password"]
        self.auth_methods = auth_methods
        if allowed_scopes is None:
            self.scope = None
        else:
            scope = data["scope"]
            if not allowed_scopes.issuperset(scope):
                invalid_scopes = ", ".join(set(scope) - allowed_scopes)
                msg = (
                    "Invalid scopes: those scope values are not allowed, "
                    'please check "AUTH_SERVER_CLIENTS" in settings: {invalid_scopes}'.format(
                        invalid_scopes=invalid_scopes
                    )
                )
                raise ValueError(msg)
            self.scope = scope

    @property
    def client_id(self):
        return str(self._id)

    def check_client_secret(self, client_secret):
        return bcrypt.checkpw(client_secret.encode(), self.pwd_hash.encode())

    def check_grant_type(self, grant_type):
        return grant_type == "client_credentials"

    def get_allowed_scope(self, scope):
        return ""

    def check_endpoint_auth_method(self, method, endpoint):
        if endpoint == "token":
            return method in self.auth_methods
        return True

    def check_token_endpoint_auth_method(self, method):
        return method in self.auth_methods

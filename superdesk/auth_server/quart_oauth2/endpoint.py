# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any
import time
import logging

from authlib.oauth2.rfc6749 import grants, ClientMixin
from authlib.jose import jwt
from superdesk.core import get_config
from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.types import Request
from superdesk.core.web import Endpoint

from .authorization_server import QuartAuthorizationServer


logger = logging.getLogger(__name__)


class OAuth2Server(Endpoint):
    server_class: type[QuartAuthorizationServer] = QuartAuthorizationServer
    grant_classes: list[type[grants.BaseGrant]] = [grants.ClientCredentialsGrant]
    add_scope_to_jwt: bool = True
    server: QuartAuthorizationServer

    def __init__(self, url: str):
        super().__init__(url, self.issue_token_endpoint, methods=["POST"], auth=False)
        self.server = self.server_class(query_client=self.query_client, save_token=self.save_token)

    @property
    def expiration_delay(self) -> int:
        return get_config(int, "AUTH_SERVER_EXPIRATION_DELAY")

    @property
    def shared_secret(self) -> str:
        return get_config(str, "AUTH_SERVER_SHARED_SECRET").strip()

    def init_app(self, app: SuperdeskAsyncApp, register_endpoint: bool = True):
        if not self.shared_secret:
            logger.warning(
                "No shared secret set, please set it using AUTH_SERVER_SHARED_SECRET "
                "environment variable or setting. Authorisation server can't be used"
            )
            return None

        app.wsgi.config["OAUTH2_ACCESS_TOKEN_GENERATOR"] = self.generate_jwt_token
        app.wsgi.config["OAUTH2_TOKEN_EXPIRES_IN"] = {"client_credentials": self.expiration_delay}
        self.server.init_app(app.wsgi)
        for grant_class in self.grant_classes:
            self.server.register_grant(grant_class)

        if register_endpoint:
            app.wsgi.register_endpoint(self)

    def query_client(self, client_id: str) -> ClientMixin | None:
        raise NotImplementedError()

    def save_token(self, token, request) -> None:
        # we don't save token as JWT signature is enough to check it
        pass

    def generate_jwt_token(self, client, grant_type, user, scope) -> str:
        header = {"alg": "HS256"}
        payload = {
            "iss": "Superdesk Auth Server",
            "iat": int(time.time()),
            "exp": int(time.time() + self.expiration_delay),
            "client_id": client.client_id,
        }
        if self.add_scope_to_jwt:
            payload["scope"] = client.scope

        return jwt.encode(header, payload, self.shared_secret).decode("utf-8")

    async def issue_token_endpoint(self, request: Request) -> Any:
        return await self.server.create_token_response()

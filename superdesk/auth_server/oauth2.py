# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import time
import logging
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import grants
from authlib.jose import jwt
import superdesk
from .models import query_client, save_token


logger = logging.getLogger(__name__)

authorization = AuthorizationServer(
    query_client=query_client,
    save_token=save_token,
)


bp = superdesk.Blueprint("auth_server", __name__)

TOKEN_ENDPOINT = "/auth_server/token"
shared_secret = None
expiration_delay = 0


@bp.route(TOKEN_ENDPOINT, methods=["POST"])
def issue_token():
    return authorization.create_token_response()


def generate_jwt_token(client, grant_type, user, scope):
    header = {"alg": "HS256"}
    payload = {
        "iss": "Superdesk Auth Server",
        "iat": int(time.time()),
        "exp": int(time.time() + expiration_delay),
        "client_id": client.client_id,
        "scope": client.scope,
    }
    return jwt.encode(header, payload, shared_secret)


def config_oauth(app):
    global expiration_delay
    expiration_delay = app.config["AUTH_SERVER_EXPIRATION_DELAY"]

    global shared_secret
    shared_secret = app.config["AUTH_SERVER_SHARED_SECRET"]
    if not shared_secret.strip():
        logger.warning(
            "No shared secret set, please set it using AUTH_SERVER_SHARED_SECRET "
            "environment variable or setting. Authorisation server can't be used"
        )
        return

    app.config["OAUTH2_ACCESS_TOKEN_GENERATOR"] = generate_jwt_token
    app.config["OAUTH2_TOKEN_EXPIRES_IN"] = {"client_credentials": expiration_delay}
    authorization.init_app(app)
    authorization.register_grant(grants.ClientCredentialsGrant)

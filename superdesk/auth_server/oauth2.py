# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from bson import ObjectId
from bson.errors import InvalidId

from superdesk import get_resource_service
from superdesk.core.module import Module

from .quart_oauth2 import OAuth2Server, OAuth2Client
from .scopes import allowed_scopes


logger = logging.getLogger(__name__)


class SuperdeskOAuth2Server(OAuth2Server):
    def query_client(self, client_id: str) -> OAuth2Client | None:
        clients_service = get_resource_service("auth_server_clients")
        try:
            client_data = clients_service.find_one(req=None, _id=ObjectId(client_id))
        except InvalidId as e:
            logger.error("Invalid 'client_id' was provided. Exception: {}".format(e))
            return None

        if client_data is None:
            return None

        return OAuth2Client(client_data, auth_methods=["client_secret_basic"], allowed_scopes=allowed_scopes)


TOKEN_ENDPOINT = "/auth_server/token"
authorization = SuperdeskOAuth2Server(TOKEN_ENDPOINT)

module = Module(name="superdesk.auth_server.oauth2", init=authorization.init_app)

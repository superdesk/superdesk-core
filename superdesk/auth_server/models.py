# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import bcrypt
from bson import ObjectId
from bson.errors import InvalidId
from authlib.oauth2.rfc6749 import ClientMixin
import superdesk
from .scopes import allowed_scopes

logger = logging.getLogger(__name__)
# client_id to OAuth2Client instance map


class OAuth2Client(ClientMixin):

    def __init__(self, data):
        self._id = data['_id']
        self.pwd_hash = data['password']
        scope = data['scope']
        if not allowed_scopes.issuperset(scope):
            invalid_scopes = ', '.join(set(scope) - allowed_scopes)
            msg = (
                'Invalid scopes: those scope values are not allowed, '
                'please check "AUTH_SERVER_CLIENTS" in settings: {invalid_scopes}'
                .format(invalid_scopes=invalid_scopes)
            )
            raise ValueError(msg)
        self.scope = scope

    @property
    def client_id(self):
        return str(self._id)

    def check_token_endpoint_auth_method(self, method):
        return method == 'client_secret_basic'

    def check_client_secret(self, client_secret):
        return bcrypt.checkpw(client_secret.encode(), self.pwd_hash.encode())

    def check_grant_type(self, grant_type):
        return grant_type == 'client_credentials'

    def get_allowed_scope(self, scope):
        return ''


def query_client(client_id):
    clients_service = superdesk.get_resource_service('auth_server_clients')
    try:
        client_data = clients_service.find_one(req=None, _id=ObjectId(client_id))
    except InvalidId as e:
        logger.error(
            "Invalid 'client_id' was provided. Exception: {}".format(e)
        )
        return None

    if client_data is None:
        return None
    return OAuth2Client(client_data)


def save_token(token, request):
    # we don't save token as JWT signature is enough to check it
    pass

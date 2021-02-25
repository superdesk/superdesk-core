# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from . import oauth2
from .clients import AuthServerClientsResource, AuthServerClientsService


def init_app(app) -> None:
    oauth2.config_oauth(app)
    superdesk.register_resource("auth_server_clients", AuthServerClientsResource, AuthServerClientsService)
    superdesk.blueprint(oauth2.bp, app)

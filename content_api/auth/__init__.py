# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core.module import Module
import superdesk
from superdesk.services import BaseService
from superdesk.publish_async.resources.module import subscriber_token_resource_config

from apps.auth import AuthResource
from .auth import AuthUsersResource


def init_app(app) -> None:
    endpoint_name = "auth"
    service = BaseService("auth", backend=superdesk.get_backend())
    AuthResource(endpoint_name, app=app, service=service)

    service = BaseService("auth_user", backend=superdesk.get_backend())
    AuthUsersResource("auth_user", app=app, service=service)


module = Module(name="content_api.auth", resources=[subscriber_token_resource_config])

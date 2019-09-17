# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .service import UsersService
from .resource import UsersResource


def init_app(app):
    """Initialize the `users` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    service = UsersService(datasource='users', backend=superdesk.get_backend())
    UsersResource(endpoint_name='users', app=app, service=service)

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
from .service import PackagesService
from .resource import PackagesResource


def init_app(app):
    """Initialize the `packages` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    endpoint_name = "packages"
    service = PackagesService(endpoint_name, backend=superdesk.get_backend())
    PackagesResource(endpoint_name, app=app, service=service)

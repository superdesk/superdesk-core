# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .service import ItemsService
from .resource import ItemsResource


def init_app(app):
    """Initialize the `items` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    service = ItemsService(datasource='archive', backend=superdesk.get_backend())
    ItemsResource(endpoint_name='archive', app=app, service=service)

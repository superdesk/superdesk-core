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
from .service import InternalItemsService, ItemsService
from .resource import InternalItemsResource, ItemsResource


def init_app(app) -> None:
    """Initialize the `items` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    endpoint_name = "items"
    service = ItemsService(endpoint_name, backend=superdesk.get_backend())
    ItemsResource(endpoint_name, app=app, service=service)

    internal_service = InternalItemsService("capi_items_internal", backend=superdesk.get_backend())
    InternalItemsResource("capi_items_internal", app=app, service=internal_service)

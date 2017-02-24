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
from .service import ItemsVersionsService
from .resource import ItemsVersionsResource


def init_app(app):
    """Initialise the items versions end point

    :param app: the API application object
    :type app: `Eve`
    """
    endpoint_name = 'items_versions'
    service = ItemsVersionsService(endpoint_name, backend=superdesk.get_backend())
    ItemsVersionsResource(endpoint_name, app=app, service=service)

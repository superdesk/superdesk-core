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
from .service import DesksService
from .resource import DesksResource


def init_app(app):
    """Initialize the `desks` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    service = DesksService(datasource="desks", backend=superdesk.get_backend())
    DesksResource(endpoint_name="desks", app=app, service=service)

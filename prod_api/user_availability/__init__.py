# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .service import UserAvailabilityService
from .resource import UserAvailabilityResource


def init_app(app) -> None:
    """Initialize the `user_availability` API endpoint for the Production API.

    :param app: the API application object
    :type app: `Eve`
    """
    service = UserAvailabilityService(datasource="user_availability", backend=superdesk.get_backend())
    UserAvailabilityResource(endpoint_name="user_availability", app=app, service=service)

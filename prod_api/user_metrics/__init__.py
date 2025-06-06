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

from .service import UserMetricsService
from .resource import UserMetricsResource


def init_app(app):
    """Initialize the user metrics resource and service.

    :param app: The superdesk app
    """
    endpoint_name = "user_metrics"
    service = UserMetricsService(endpoint_name, backend=superdesk.get_backend())
    UserMetricsResource(endpoint_name, app=app, service=service)

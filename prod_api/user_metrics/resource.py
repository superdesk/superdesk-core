# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.auth_server.scopes import Scope


class UserMetricsResource(Resource):
    """Resource for exposing user metrics through the production API."""

    url = "user_metrics"
    item_methods = []
    resource_methods = ["GET"]

    schema = {
        "date": {"type": "date"},
        "user": {"type": "objectid"},
        "name": {"type": "string"},
        "value": {"type": "number"},
    }

    privileges = {
        "GET": Scope.USERS_READ.name,
    }

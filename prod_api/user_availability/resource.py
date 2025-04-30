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
from superdesk.metadata.utils import item_url
from superdesk.auth_server.scopes import Scope


class UserAvailabilityResource(Resource):
    """Resource for exposing user availability through the production API."""

    url = "user_availability"
    item_url = item_url
    item_methods = ["GET"]
    resource_methods = ["GET"]
    schema = {
        "date": {"type": "string"},
        "user": {"type": "objectid"},
        "status": {"type": "string"},
    }
    datasource = {"source": "user_availability", "default_sort": [("date", 1)]}
    privileges = {"GET": Scope.USERS_READ.name}

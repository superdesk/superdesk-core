# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.metadata.utils import item_url
from superdesk.auth_server.scopes import Scope


class DesksResource(Resource):
    url = "desks"
    item_url = item_url
    item_methods = ["GET"]
    resource_methods = ["GET"]
    allow_unknown = True
    datasource = {"source": "desks", "default_sort": [("name", 1)]}
    privileges = {"GET": Scope.DESKS_READ.name}

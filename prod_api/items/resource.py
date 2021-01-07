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
from superdesk.metadata.item import metadata_schema
from superdesk.auth_server.scopes import Scope


# NOTE: since schema is not defined here, setting up a projection explicitly is required,
# otherwise default `eve` fields (projection) will be applied e.q. `{'_id': 1}`
# and it will cut off all required data.
# https://github.com/pyeve/eve/blob/afd573d9254a9a23393f35760e9c515300909ccd/eve/io/base.py#L420
projection = {key: 1 for key in metadata_schema}
projection.update(
    {
        "fields_meta": 0,
    }
)


class ItemsResource(Resource):
    url = "items"
    item_url = item_url
    item_methods = ["GET"]
    resource_methods = ["GET"]
    datasource = {
        "source": "archive",
        "search_backend": "elastic",
        "default_sort": [("_updated", -1)],
        "projection": projection,
    }
    privileges = {"GET": Scope.ARCHIVE_READ.name}

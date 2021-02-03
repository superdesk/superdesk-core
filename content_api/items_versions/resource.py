# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from content_api import MONGO_PREFIX
from content_api.items.resource import schema
from copy import deepcopy


class ItemsVersionsResource(Resource):
    item_url = 'regex("[\w,.:-]+")'
    version_schema = deepcopy(schema)
    version_schema["_id_document"] = {"type": "string"}
    schema = version_schema

    datasource = {"source": "items_versions"}

    mongo_indexes = {"_id_document_": [("_id_document", 1)]}

    item_methods = ["GET"]
    resource_methods = ["GET"]
    internal_resource = True
    mongo_prefix = MONGO_PREFIX

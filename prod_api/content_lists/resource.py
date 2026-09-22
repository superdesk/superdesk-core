# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.types import AuthServerScope


# NOTE: no static datasource ``filter`` on purpose: it would be AND-ed with any
# client ``where`` and make disabled documents unreachable. The default
# ``enabled`` filtering is applied in the services instead, so it can be
# overridden with the ``enabled`` query parameter.


class ContentListsResource(Resource):
    url = "content_lists"
    resource_title = "content_lists"
    item_methods: list = []
    resource_methods = ["GET"]
    allow_unknown = True
    datasource = {"source": "content_lists", "default_sort": [("name", 1)]}
    privileges = {"GET": AuthServerScope.CONTENT_LISTS_READ.name}


class ContentListItemsResource(Resource):
    url = 'content_lists/<regex("[a-f0-9]{24}"):list_id>/items'
    resource_title = "content_list_items"
    item_methods: list = []
    resource_methods = ["GET"]
    allow_unknown = True
    # partial schema, so ``list_id`` is stored and queried as an ObjectId
    # (the internal api stores it that way); other fields stay unknown/passthrough
    schema = {"list_id": {"type": "objectid"}}
    datasource = {"source": "content_list_items", "default_sort": [("position", 1)]}
    privileges = {"GET": AuthServerScope.CONTENT_LISTS_READ.name}

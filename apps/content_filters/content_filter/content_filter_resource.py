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


class ContentFilterResource(Resource):
    schema = {
        "name": {"type": "string", "required": True, "nullable": False, "empty": False, "iunique": True},
        "content_filter": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "expression": {
                        "type": "dict",
                        "schema": {
                            "fc": {"type": "list", "schema": Resource.rel("filter_conditions", True)},
                            "pf": {"type": "list", "schema": Resource.rel("content_filters", True)},
                        },
                    }
                },
            },
        },
        "is_global": {"type": "boolean", "default": False},
        "is_archived_filter": {"type": "boolean", "default": False},
        "api_block": {"type": "boolean", "default": False},
    }

    additional_lookup = {"url": 'regex("[\w,.:-]+")', "field": "name"}

    privileges = {"POST": "content_filters", "PATCH": "content_filters", "DELETE": "content_filters"}

    mongo_indexes = {
        "name_1": ([("name", 1)], {"unique": True}),
    }

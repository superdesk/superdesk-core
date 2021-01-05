#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from superdesk.utils import ListCursor
from flask import current_app as app


class AllowedValuesResource(superdesk.Resource):
    """Resource allowing apps to set allowed values which can be used by client to filter certain options."""

    resource_methods = ["GET"]
    item_methods = []
    schema = {
        "items": {
            "type": "list",
        },
    }


class AllowedValuesService(superdesk.Service):
    def get(self, req, lookup):
        allowed = []
        for resource, config in app.config.get("DOMAIN", {}).items():
            for field, field_config in config.get("schema", {}).items():
                if field_config.get("allowed"):
                    allowed.append(
                        {
                            "_id": "{}.{}".format(resource, field),
                            "items": [str(item) for item in field_config["allowed"]],
                        }
                    )
        return ListCursor(allowed)


def init_app(app):
    AllowedValuesResource("allowed_values", app, AllowedValuesService())

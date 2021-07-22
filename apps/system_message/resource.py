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


class SystemMessagesResource(Resource):
    schema = {
        "is_active": {"type": "boolean", "default": False},
        "type": {
            "type": "string",
            "allowed": ["warning", "alert", "primary", "success", "highlight", "light"],
            "required": True,
        },
        "message_title": {"type": "string", "required": True},
        "message": {"type": "string", "required": True, "maxlength": 200},
        "user_id": Resource.rel("users"),
    }

    resource_methods = ["GET", "POST"]
    item_methods = ["GET", "PATCH", "DELETE"]
    privileges = {"POST": "system_messages", "PATCH": "system_messages", "DELETE": "system_messages"}

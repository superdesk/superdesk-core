# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from superdesk.resource import Resource
import superdesk
from content_api import MONGO_PREFIX


logger = logging.getLogger(__name__)


class AuthUsersResource(Resource):
    """This resource is for authentication only.

    On users `find_one` never returns a password due to the projection.
    """

    datasource = {"source": "users"}
    schema = {
        "email": {
            "type": "string",
        },
        "password": {
            "type": "string",
        },
        "is_enabled": {"type": "boolean"},
        "is_approved": {"type": "boolean"},
    }
    item_methods = []
    resource_methods = []
    internal_resource = True
    mongo_prefix = MONGO_PREFIX


class AuthResource(Resource):
    schema = {
        "email": {"type": "string", "required": True},
        "password": {"type": "string", "required": True},
        "token": {"type": "string"},
        "user": Resource.rel("users", True),
    }
    resource_methods = ["POST"]
    item_methods = ["GET", "DELETE"]
    public_methods = ["POST", "DELETE"]
    extra_response_fields = ["user", "token", "username"]
    datasource = {"source": "auth"}


superdesk.intrinsic_privilege("auth", method=["DELETE"])

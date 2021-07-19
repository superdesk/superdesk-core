# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
import logging
import superdesk

from datetime import timedelta
from flask import request, current_app as app, json
from eve.auth import TokenAuth
from superdesk.resource import Resource
from superdesk.errors import SuperdeskApiError
from superdesk import (
    get_resource_service,
    get_resource_privileges,
    get_no_resource_privileges,
    get_intrinsic_privileges,
)
from superdesk.utc import utcnow
from flask_babel import _

logger = logging.getLogger(__name__)


class AuthUsersResource(Resource):
    """This resource is for authentication only.

    On users `find_one` never returns a password due to the projection.
    """

    datasource = {"source": "users"}
    schema = {
        "username": {
            "type": "string",
        },
        "password": {
            "type": "string",
        },
        "password_changed_on": {"type": "datetime", "nullable": True},
        "is_active": {"type": "boolean"},
        "is_enabled": {"type": "boolean"},
    }
    item_methods = []
    resource_methods = []
    internal_resource = True


class AuthResource(Resource):
    schema = {
        "username": {"type": "string", "required": True},
        "password": {"type": "string", "required": True},
        "token": {"type": "string"},
        "user": Resource.rel("users", True),
    }

    resource_methods = ["POST"]
    item_methods = ["GET", "DELETE"]
    public_methods = ["POST"]
    extra_response_fields = ["user", "token", "username"]
    datasource = {"source": "auth"}
    mongo_indexes = {"token": ([("token", 1)], {"background": True})}


superdesk.intrinsic_privilege("auth", method=["DELETE"])


class SuperdeskTokenAuth(TokenAuth):
    """Superdesk Token Auth"""

    def check_permissions(self, resource, method, user):
        """Checks user permissions.

        1. If there's no user associated with the request or HTTP Method is GET or the Resource is a Flask Blueprint
        then return True.
        2. Get User's Privileges
        3. Intrinsic Privileges:
            Check if resource has intrinsic privileges.
                If it has then check if HTTP Method is allowed.
                    Return True if `is_authorized()` on the resource service returns True.
                    Otherwise, raise ForbiddenError.
                HTTP Method not allowed continue
            No intrinsic privileges continue
        4. User's Privileges
            Get Resource Privileges and validate it against user's privileges. Return True if validation is successful.
            Otherwise continue.
        5. If method didn't return True, then user is not authorized to perform the requested operation on the resource.
        """

        # Step 1:
        if not user:
            return True

        if resource == "_blueprint":
            return True

        # Step 2: Get User's Privileges
        get_resource_service("users").set_privileges(user, flask.g.role)

        try:
            resource_privileges = get_resource_privileges(resource).get(method, None)
        except KeyError:
            resource_privileges = None

        if method == "GET" and not resource_privileges:
            return True

        # Step 3: Intrinsic Privileges
        message = _("Insufficient privileges for the requested operation.")
        intrinsic_privileges = get_intrinsic_privileges()
        if intrinsic_privileges.get(resource) and method in intrinsic_privileges[resource]:
            service = get_resource_service(resource)
            authorized = service.is_authorized(
                user_id=str(user.get("_id")), _id=request.view_args.get("_id"), method=method
            )

            if not authorized:
                raise SuperdeskApiError.forbiddenError(message=message)

            return authorized

        # Step 4: User's privileges
        privileges = user.get("active_privileges", {})

        if not resource_privileges and get_no_resource_privileges(resource):
            return True

        if privileges.get(resource_privileges, False):
            return True

        # Step 5:
        raise SuperdeskApiError.forbiddenError(message=message)

    def check_auth(self, token, allowed_roles, resource, method):
        """Check if given token is valid.

        If token is valid it updates session and checks permissions.
        """
        auth_service = get_resource_service("auth")
        user_service = get_resource_service("users")
        auth_token = auth_service.find_one(token=token, req=None)
        if auth_token:
            user_id = str(auth_token["user"])
            flask.g.user = user_service.find_one(req=None, _id=user_id)
            flask.g.role = user_service.get_role(flask.g.user)
            flask.g.auth = auth_token
            flask.g.auth_value = auth_token["user"]
            if method in ("POST", "PUT", "PATCH") or method == "GET" and not request.args.get("auto"):
                now = utcnow()
                auth_updated = False
                if auth_token[app.config["LAST_UPDATED"]] + timedelta(seconds=10) < now:  # update once every 10s max
                    auth_service.update_session({app.config["LAST_UPDATED"]: now})
                    auth_updated = True
                if not flask.g.user.get("last_activity_at") or auth_updated:
                    user_service.system_update(
                        flask.g.user["_id"], {"last_activity_at": now, "_updated": now}, flask.g.user
                    )

            return self.check_permissions(resource, method, flask.g.user)

    def authorized(self, allowed_roles, resource, method):
        """Ignores auth on home endpoint."""
        if not resource:
            return True
        return super(SuperdeskTokenAuth, self).authorized(allowed_roles, resource, method)

    def authenticate(self):
        """Returns 401 response with CORS headers."""
        raise SuperdeskApiError.unauthorizedError()

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
from inspect import isawaitable

import superdesk

from eve.auth import TokenAuth

from superdesk.core.auth.utils import set_user_request_auth_data, clear_user_request_auth_data
from superdesk.flask import session, request
from superdesk.resource import Resource
from superdesk.errors import SuperdeskApiError
from superdesk import (
    get_resource_service,
    get_resource_privileges,
    get_no_resource_privileges,
    get_intrinsic_privileges,
)
from quart_babel import gettext as _

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

    async def check_permissions(self, resource, method, user):
        """Checks user permissions.

        1. If there's no user associated with the request or HTTP Method is GET or the Resource is a Flask Blueprint
        then return True.
        2. Intrinsic Privileges:
            Check if resource has intrinsic privileges.
                If it has then check if HTTP Method is allowed.
                    Return True if `is_authorized()` on the resource service returns True.
                    Otherwise, raise ForbiddenError.
                HTTP Method not allowed continue
            No intrinsic privileges continue
        3. User's Privileges
            Get Resource Privileges and validate it against user's privileges. Return True if validation is successful.
            Otherwise continue.
        4. If method didn't return True, then user is not authorized to perform the requested operation on the resource.
        """

        # Step 1:
        if not user:
            return True

        if resource == "_blueprint":
            return True

        try:
            resource_privileges = get_resource_privileges(resource).get(method, None)
        except KeyError:
            resource_privileges = None

        if method == "GET" and not resource_privileges:
            return True

        # Step 2: Intrinsic Privileges
        message = _("Insufficient privileges for the requested operation.")
        intrinsic_privileges = get_intrinsic_privileges()
        if intrinsic_privileges.get(resource) and method in intrinsic_privileges[resource]:
            service = get_resource_service(resource)
            authorized = await service.is_authorized(
                user_id=str(user.get("_id")), _id=request.view_args.get("_id"), method=method
            )

            if not authorized:
                raise SuperdeskApiError.forbiddenError(message=message)

            return authorized

        # Step 3: User's privileges
        privileges = user.get("active_privileges", {})

        if not resource_privileges and get_no_resource_privileges(resource):
            return True

        if privileges.get(resource_privileges, False):
            return True

        # Step 4:
        raise SuperdeskApiError.forbiddenError(message=message)

    async def check_auth(self, token, allowed_roles, resource, method):
        """Check if given token is valid.

        If token is valid it updates session and checks permissions.
        """

        try:
            user_dict = await set_user_request_auth_data(token, request)
            return await self.check_permissions(resource, method, user_dict)
        except SuperdeskApiError as error:
            if error.status_code != 401:
                # If this is not an authentication error, then raise it
                raise

        # The user is not authenticated, clear the request auth data and return False
        clear_user_request_auth_data(request)
        return False

    async def authorized(self, allowed_roles, resource, method):
        """Ignores auth on home endpoint."""
        if not resource:
            return True

        # authenticate using session token only if there is no authorization header
        if session.get("session_token") and not request.headers.get("Authorization"):
            return await self.check_auth(session["session_token"], allowed_roles, resource, method)

        # use authorization token
        response = super(SuperdeskTokenAuth, self).authorized(allowed_roles, resource, method)
        if isawaitable(response):
            response = await response
        return response

    def authenticate(self):
        """Returns 401 response with CORS headers."""
        raise SuperdeskApiError.unauthorizedError()

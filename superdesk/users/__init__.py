# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask_babel import lazy_gettext
import superdesk
from apps import auth

from .users import UsersResource
from .services import UsersService, DBUsersService, is_admin  # noqa


def init_app(app) -> None:
    endpoint_name = "users"
    service = DBUsersService(endpoint_name, backend=superdesk.get_backend())
    UsersResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="users", label=lazy_gettext("User Management"), description=lazy_gettext("User can manage users.")
    )

    # Registering with intrinsic privileges because: A user should be allowed to update their own profile.
    superdesk.intrinsic_privilege(resource_name="users", method=["PATCH"])

    app.client_config.setdefault("user", {}).update(
        {
            "username_pattern": app.config.get("USER_USERNAME_PATTERN"),
        }
    )


def get_user_from_request(required=False):
    """
    Get user authenticated for current request.

    :param boolean required: if True and there is no user it will raise an error
    """

    return auth.get_user(required)

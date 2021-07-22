# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any
from flask_babel import lazy_gettext
import superdesk
from apps.auth import AuthResource
from .ldap import ADAuthService, ADAuth, ImportUserProfileResource, ImportUserProfileService  # noqa
from .commands import ImportUserProfileFromADCommand  # noqa
from .users_service import ADUsersService, UsersResource, is_admin  # NOQA


def init_app(app) -> None:
    endpoint_name = "users"
    service: Any = ADUsersService(endpoint_name, backend=superdesk.get_backend())
    UsersResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="users", label=lazy_gettext("User Management"), description=lazy_gettext("User can manage users.")
    )

    # Registering with intrinsic privileges because: A user should be allowed to update their own profile.
    superdesk.intrinsic_privilege(resource_name="users", method=["PATCH"])

    # we need to use the same endpoint as database auth because it is called in the same location
    endpoint_name = "auth_db"
    service = ADAuthService(endpoint_name, backend=superdesk.get_backend())
    AuthResource(endpoint_name, app=app, service=service)

    endpoint_name = ImportUserProfileResource.url
    service = ImportUserProfileService(endpoint_name, backend=superdesk.get_backend())
    ImportUserProfileResource(endpoint_name, app=app, service=service)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from .roles import RolesResource, RolesService
import superdesk


def init_app(app):
    endpoint_name = "roles"
    service = RolesService(endpoint_name, backend=superdesk.get_backend())
    RolesResource(endpoint_name, app=app, service=service)

    superdesk.privilege(name="roles", label="Roles Management", description="User can manage roles.")

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from superdesk import get_resource_service


class RolesTestCase(TestCase):

    roles = [{"name": "test", "privileges": {"ingest": 1, "archive": 1, "fetch": 1}}]

    users = [
        {
            "username": "foobar",
            "first_name": "foo",
            "last_name": "bar",
            "user_type": "user",
            "display_name": "Foo Bar",
            "is_enabled": True,
            "is_active": True,
        }
    ]

    def setUp(self):
        self.app.data.insert("roles", self.roles)
        self.users[0]["role"] = self.roles[0]["_id"]
        self.app.data.insert("users", self.users)

    def test_invoking_on_revoked_privileges_event(self):
        def on_revoke_roles(role, role_users):
            self.assertEqual(role.get("name"), "test")
            self.assertEqual(len(role_users), 1)
            self.assertEqual(role_users[0]["username"], "foobar")
            pass

        self.app.on_role_privileges_updated -= on_revoke_roles
        self.app.on_role_privileges_updated += on_revoke_roles
        get_resource_service("roles").patch(self.roles[0]["_id"], {"privileges": {"ingest": 0}})

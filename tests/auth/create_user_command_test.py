# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service
from os.path import dirname, join
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.auth.db.commands import CreateUserCommand, ImportUsersCommand


class CreateUserCommandTestCase(TestCase):

    def test_create_user_command(self):
        if not self.app.config.get('LDAP_SERVER'):
            user = {'username': 'foo', 'password': 'bar', 'email': 'baz', 'password_changed_on': utcnow()}
            cmd = CreateUserCommand()
            cmd.run(user['username'], user['password'], user['email'], admin=True)
            auth_user = get_resource_service('auth_db').authenticate(user)
            self.assertEquals(auth_user['username'], user['username'])

            cmd.run(user['username'], user['password'], user['email'], admin=True)
            auth_user2 = get_resource_service('auth_db').authenticate(user)
            self.assertEquals(auth_user2['username'], user['username'])
            self.assertEquals(auth_user2['_id'], auth_user['_id'])

    def test_create_user_command_no_update(self):
        if not self.app.config.get('LDAP_SERVER'):
            user = {'username': 'foo', 'password': 'bar', 'email': 'baz', 'password_changed_on': utcnow()}
            cmd = CreateUserCommand()
            cmd.run(
                user['username'], user['password'], user['email'], admin=True
            )
            cmd.run(
                user['username'], "new_password", user['email'], admin=True
            )
            get_resource_service('auth_db').authenticate(user)

    def test_import_users(self):
        """users:import is working with JSON files"""
        roles = [
            {'name': 'Writer', 'privileges': {}},
            {'name': 'Admin', 'privileges': {}},
        ]

        self.app.data.insert('roles', roles)

        cmd = ImportUsersCommand()
        fixtures_path = join(dirname(__file__), 'fixtures')
        import_file = join(fixtures_path, "import_users_test.json")
        cmd.run(None, import_file)
        users_service = get_resource_service('users')
        roles_services = get_resource_service('roles')

        found_user = users_service.find_one(req=None, username="toto")
        self.assertIsNotNone(found_user)
        role_id = roles_services.find_one(req=None, name="Writer")['_id']
        self.assertEqual(found_user["role"], role_id)

        found_user = users_service.find_one(req=None, username="titi")
        self.assertIsNotNone(found_user)
        role_id = roles_services.find_one(req=None, name="Admin")['_id']
        self.assertEqual(found_user["role"], role_id)

        found_user = users_service.find_one(req=None, username="invalid_no_email")
        self.assertIsNone(found_user)

        found_user = users_service.find_one(req=None, username="invalid_unknown_role")
        self.assertIsNone(found_user)

    def test_import_users_csv(self):
        """users:import is working with CSV files"""
        roles = [
            {'name': 'Writer', 'privileges': {}},
            {'name': 'Admin', 'privileges': {}},
        ]

        self.app.data.insert('roles', roles)

        cmd = ImportUsersCommand()
        fixtures_path = join(dirname(__file__), 'fixtures')
        import_file = join(fixtures_path, "import_users_test.csv")
        cmd.run(["username", "first_name", "last_name", "sign_off", "email", "role"], import_file)
        users_service = get_resource_service('users')
        roles_services = get_resource_service('roles')

        found_user = users_service.find_one(req=None, username="mr_x")
        self.assertIsNotNone(found_user)
        role_id = roles_services.find_one(req=None, name="Writer")['_id']
        self.assertEqual(found_user["role"], role_id)

        found_user = users_service.find_one(req=None, username="ms_x")
        self.assertIsNotNone(found_user)
        role_id = roles_services.find_one(req=None, name="Admin")['_id']
        self.assertEqual(found_user["role"], role_id)

    def test_import_users_no_activation_email(self):
        """users:import does not send activation email"""
        roles = [
            {'name': 'Writer', 'privileges': {}},
            {'name': 'Admin', 'privileges': {}},
        ]

        self.app.data.insert('roles', roles)

        cmd = ImportUsersCommand()
        fixtures_path = join(dirname(__file__), 'fixtures')
        import_file = join(fixtures_path, "import_users_test.json")

        with self.app.app_context():
            with self.app.mail.record_messages() as outbox:
                assert len(outbox) == 0
                cmd.run(None, import_file)
                assert len(outbox) == 0

    def test_import_users_activation_email(self):
        """users:import sends activation link"""
        roles = [
            {'name': 'Writer', 'privileges': {}},
            {'name': 'Admin', 'privileges': {}},
        ]

        self.app.data.insert('roles', roles)

        cmd = ImportUsersCommand()
        fixtures_path = join(dirname(__file__), 'fixtures')
        import_file = join(fixtures_path, "import_users_test.json")

        with self.app.app_context():
            with self.app.mail.record_messages() as outbox:
                assert len(outbox) == 0
                cmd.run(None, import_file, activation_email=True)
                assert len(outbox) == 2

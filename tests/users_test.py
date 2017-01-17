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

from datetime import timedelta
from unittest.mock import patch
from superdesk import get_backend
from superdesk.utc import utcnow
from superdesk.tests import TestCase
from superdesk.users.services import UsersService, compare_preferences
from apps.auth.db.reset_password import ResetPasswordService


class PrivilegesTestCase(TestCase):

    def setUp(self):
        with self.app.app_context():
            self.service = UsersService('users', backend=get_backend())

    def test_admin_has_all_privileges(self):
        with self.app.app_context():
            user = {'user_type': 'administrator'}
            self.service.set_privileges(user, None)
            self.assertEqual(user['active_privileges']['users'], 1)

    def test_user_has_merged_privileges(self):
        with self.app.app_context():
            user = {'user_type': 'user', 'privileges': {'users': 1}}
            role = {'privileges': {'archive': 1}}
            self.service.set_privileges(user, role)
            self.assertEqual(user['active_privileges']['users'], 1)
            self.assertEqual(user['active_privileges']['archive'], 1)

    def test_user_with_privilege_can_change_his_role(self):
        with self.app.app_context():
            flask.g.user = {'user_type': 'administrator'}
            ids = self.service.create([{'name': 'user', 'user_type': 'administrator'}])
            doc_old = self.service.find_one(None, _id=ids[0])
            self.service.update(ids[0], {'role': '1'}, doc_old)
            self.assertIsNotNone(self.service.find_one(req=None, role='1'))

    def test_compare_preferences(self):
        original_preferences = {
            "unlock": 1,
            "archive": 1,
            "spike": 1,
            "unspike": 1,
            "ingest_move": 0
        }

        updated_preferences = {
            "unlock": 0,
            "archive": 1,
            "spike": 1,
            "ingest": 1,
            "ingest_move": 1,
        }

        added, removed, modified = compare_preferences(original_preferences, updated_preferences)
        self.assertEqual(1, len(added))
        self.assertEqual(1, len(removed))
        self.assertEqual(2, len(modified))
        self.assertTrue((1, 0) in modified.values())
        self.assertTrue((0, 1) in modified.values())


class UserTokenTestCase(TestCase):

    def setUp(self):
        self.service = ResetPasswordService('tokens', backend=get_backend())

    @patch('apps.auth.db.reset_password.get_random_string', return_value='random')
    def test_store_token(self, get_random_string):
        now = utcnow()
        doc = {'user': 'foo', 'email': 'foo@example.com', '_id': 'foo'}
        with patch.object(self.service.backend, 'create') as create:
            with patch('apps.auth.db.reset_password.utcnow', return_value=now):
                self.service.store_reset_password_token(doc, doc['email'], 10, doc['_id'])
            create.assert_called_with('tokens', [{
                'user': 'foo',
                'email': 'foo@example.com',
                '_id': 'foo',
                '_created': now,
                '_updated': now,
                'expire_time': now + timedelta(days=10),
                'token': 'random',
            }])

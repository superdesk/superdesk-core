
from unittest.mock import patch
from bson import ObjectId
from datetime import timedelta

from superdesk.utc import utcnow
from superdesk.tests import TestCase
from apps.auth.session_purge import RemoveExpiredSessions
from apps.auth import is_current_user_admin


class AuthTestCase(TestCase):

    def test_remove_expired_sessions_syncs_online_users(self):
        sess_id = ObjectId()
        user_ids = self.app.data.insert('users', [
            {'name': 'foo', 'username': 'foo', 'session_preferences': {'test': {}}},
            {'name': 'bar', 'username': 'bar', 'session_preferences': {'bar': {}, str(sess_id): {}}},
        ])

        self.assertEqual(2, len(user_ids))

        self.app.data.insert('auth', [
            {'user': user_ids[0], '_updated': utcnow() - timedelta(days=50)},
            {'user': user_ids[1], '_updated': utcnow()},
            {'_id': sess_id, 'user': user_ids[1], '_updated': utcnow()}
        ])

        RemoveExpiredSessions().run()

        users = self.app.data.find_list_of_ids('users', user_ids)

        self.assertEqual({}, users[0]['session_preferences'])
        self.assertEqual({str(sess_id): {}}, users[1]['session_preferences'])

    def test_is_current_user_admin(self):
        with patch('apps.auth.get_user', return_value={}):
            self.assertFalse(is_current_user_admin())

        with patch('apps.auth.get_user', return_value={'user_type': 'administrator'}):
            self.assertTrue(is_current_user_admin())

    def test_session_expiry_date_update(self):
        user_ids = self.app.data.insert('users', [
            {'username': 'foo', 'user_type': 'administrator'},
        ])
        self.app.data.insert('auth', [
            {'user': user_ids[0], '_updated': utcnow() - timedelta(minutes=5), 'token': 'foo'},
        ])

        with self.app.test_request_context('/users', method='POST'):
            self.app.auth.check_auth('foo', [], 'users', 'POST')
            auth = self.app.data.find_one('auth', None, token='foo')
            self.assertGreaterEqual(auth['_updated'], utcnow() - timedelta(seconds=1))

            self.app.data.update('auth', auth['_id'], {'_updated': utcnow() - timedelta(seconds=10)}, auth)

            self.app.auth.check_auth('foo', [], 'users', 'POST')
            auth = self.app.data.find_one('auth', None, token='foo')
            self.assertLess(auth['_updated'], utcnow() - timedelta(seconds=1))

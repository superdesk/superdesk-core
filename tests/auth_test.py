
from bson import ObjectId
from datetime import timedelta
from superdesk.utc import utcnow
from superdesk.tests import TestCase
from apps.auth.session_purge import RemoveExpiredSessions


class AuthTestCase(TestCase):

    def test_remove_expired_sessions_syncs_online_users(self):
        sess_id = ObjectId()
        user_ids = self.app.data.insert('users', [
            {'name': 'foo', 'session_preferences': {'test': {}}},
            {'name': 'bar', 'session_preferences': {'bar': {}, str(sess_id): {}}},
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

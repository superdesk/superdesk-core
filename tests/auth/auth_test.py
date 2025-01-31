from unittest.mock import patch
from bson import ObjectId
from datetime import timedelta
from flask import session

from superdesk.utc import utcnow
from superdesk.tests import TestCase
from apps.auth.session_purge import RemoveExpiredSessions
from apps.auth import is_current_user_admin


class AuthTestCase(TestCase):
    test_context = False  # avoid request context

    def test_remove_expired_sessions_syncs_online_users(self):
        sess_id = ObjectId()
        user_ids = self.app.data.insert(
            "users",
            [
                {"name": "foo", "username": "foo", "session_preferences": {"test": {}}},
                {"name": "bar", "username": "bar", "session_preferences": {"bar": {}, str(sess_id): {}}},
            ],
        )
        self.assertEqual(2, len(user_ids))
        sessions = [
            {"user": user_ids[0], "_updated": utcnow() - timedelta(days=50)},
            {"user": user_ids[1], "_updated": utcnow()},
            {"_id": sess_id, "user": user_ids[1], "_updated": utcnow()},
        ]

        self.app.data.insert("auth", sessions)
        _ids = [_auth["user"] for _auth in self.app.data.find_all("auth")]
        self.assertEqual(3, len(_ids))

        self.app.data.insert(
            "archive",
            [
                {
                    "_id": "locked-item",
                    "lock_session": str(sessions[0]["_id"]),
                    "lock_user": str(user_ids[0]),
                    "state": "in_progress",
                    "task": {"desk": ObjectId()},
                }
            ],
        )

        RemoveExpiredSessions().run()

        # don't expose user preferences
        users = self.app.data.find_list_of_ids("users", user_ids)
        self.assertNotIn("session_preferences", users[0])
        self.assertNotIn("session_preferences", users[1])
        # ensure that expired auth tokens were removed
        _ids = [_auth["user"] for _auth in self.app.data.find_all("auth")]
        self.assertEqual(2, len(_ids))
        self.assertEqual(user_ids[1], _ids[0])
        self.assertEqual(user_ids[1], _ids[1])
        items = self.app.data.find_all("archive")
        assert items[0]["lock_user"] is None
        assert items[0]["lock_session"] is None

    def test_is_current_user_admin(self):
        with patch("apps.auth.get_user", return_value={}):
            self.assertFalse(is_current_user_admin())

        with patch("apps.auth.get_user", return_value={"user_type": "administrator"}):
            self.assertTrue(is_current_user_admin())

    def test_session_expiry_date_update(self):
        user_ids = self.app.data.insert(
            "users",
            [
                {"username": "foo", "user_type": "administrator"},
            ],
        )
        initial_updated = utcnow() - timedelta(minutes=5)
        self.app.data.insert(
            "auth",
            [
                {"user": user_ids[0], "_updated": initial_updated, "token": "foo"},
            ],
        )

        with self.app.test_request_context("/users", method="POST"):
            self.app.auth.check_auth("foo", [], "users", "POST")
            auth = self.app.data.find_one("auth", None, token="foo")
            self.assertGreaterEqual(auth["_updated"], utcnow() - timedelta(seconds=1))
            user = self.app.data.find_one("users", req=None, username="foo")
            self.assertEqual(user["last_activity_at"], auth["_updated"])

            self.app.data.update("auth", auth["_id"], {"_updated": utcnow() - timedelta(seconds=5)}, auth)

            self.app.auth.check_auth("foo", [], "users", "POST")
            auth = self.app.data.find_one("auth", None, token="foo")
            self.assertLess(auth["_updated"], utcnow() - timedelta(seconds=1))

    def test_session_with_auth_token(self):
        user_ids = self.app.data.insert(
            "users",
            [
                {"username": "foo", "user_type": "administrator"},
                {"username": "bar", "user_type": "user"},
            ],
        )
        auth_ids = self.app.data.insert(
            "auth",
            [
                {"user": user_ids[0], "_updated": utcnow(), "token": "foo"},
                {"user": user_ids[1], "_updated": utcnow(), "token": "bar"},
            ],
        )
        headers = {"Authorization": "token foo"}

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["session_token"] = "bar"

        with client:
            response = client.get("/api/users", headers=headers)
            self.assertEqual(200, response.status_code)
            assert session["session_token"] == "foo"

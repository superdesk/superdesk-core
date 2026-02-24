import json
from superdesk.tests import TestCase, setup_db_user
from superdesk import get_resource_service


class SessionsSecurityTestCase(TestCase):
    def setUp(self):
        self.endpoint = "sessions"
        self.service = get_resource_service(self.endpoint)
        self.headers = [("Content-Type", "application/json")]

    async def test_nosql_injection_token_regex(self):
        await setup_db_user(self, None)

        # The setup_db_user creates a session.
        # We can try to find it using regex on token.

        # First, get all sessions to see what we have
        resp = await self.client.get(f"/api/{self.endpoint}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = await resp.get_json()
        self.assertGreaterEqual(len(data["_items"]), 1)

        # We don't know the token value easily, but we know it exists in the DB.
        # Let's try to filter by token existence or regex.

        # Regex matching any token
        where_clause = json.dumps({"token": {"$regex": ".*"}})

        resp = await self.client.get(f"/api/{self.endpoint}?where={where_clause}", headers=self.headers)

        # Expect 400 Bad Request
        self.assertEqual(resp.status_code, 400)
        data = await resp.get_json()
        self.assertIn("Filtering by token is not allowed", data["_message"])

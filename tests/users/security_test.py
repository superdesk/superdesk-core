import json

from superdesk.tests import TestCase, setup_db_user
from superdesk import get_resource_service


class UsersSecurityTestCase(TestCase):
    def setUp(self):
        self.endpoint = "users"
        self.service = get_resource_service(self.endpoint)
        self.headers = [("Content-Type", "application/json")]

    async def test_nosql_injection_password_regex(self):
        # Authenticate as admin (setup_db_user creates test_user which is admin)
        await setup_db_user(self, None)

        # Create a victim user with a known password
        user_data = {
            "username": "victim",
            "password": "secretpassword",
            "email": "victim@example.com",
            "is_active": True,
        }
        # self.service.post is synchronous
        self.service.post([user_data])

        # Verify user exists
        resp = await self.client.get(f'/api/{self.endpoint}?where={{"username":"victim"}}', headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = await resp.get_json()
        self.assertEqual(len(data["_items"]), 1)

        # Attempt NoSQL injection to guess password
        # This should NOT return the user if the vulnerability is fixed (or if we block regex on password)
        # But currently it IS vulnerable, so it SHOULD return the user.

        # Regex matching the start of the password
        where_clause = json.dumps({"username": "victim", "password": {"$regex": "^secret.*"}})

        resp = await self.client.get(f"/api/{self.endpoint}?where={where_clause}", headers=self.headers)
        # Expect 400 Bad Request because we blocked password filtering
        self.assertEqual(resp.status_code, 400)
        data = await resp.get_json()
        self.assertIn("Filtering by password is not allowed", data["_message"])

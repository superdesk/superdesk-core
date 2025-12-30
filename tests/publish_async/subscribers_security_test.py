import json
from superdesk.tests import TestCase, setup_db_user
from superdesk.publish_async.resources.subscribers.service import SubscribersService
from superdesk import get_resource_service


class SubscribersSecurityTestCase(TestCase):
    def setUp(self):
        self.endpoint = "subscribers"
        self.service = get_resource_service("subscribers")
        self.headers = [("Content-Type", "application/json")]

    async def test_nosql_injection_password_regex(self):
        """
        Test that we cannot use regex to guess the password in destinations.config
        """
        await setup_db_user(self, None)

        # Create a subscriber with a password
        subscriber = {
            "name": "Vulnerable Subscriber",
            "is_active": True,
            "email": "test@example.com",
            "subscriber_type": "digital",
            "destinations": [
                {
                    "name": "Test Destination",
                    "format": "json",
                    "delivery_type": "http_push",
                    "config": {"password": "SuperSecretPassword123", "url": "http://example.com"},
                }
            ],
        }

        await self.service.create([subscriber])

        # Attempt to find the subscriber by guessing the password start
        # This should be BLOCKED

        # Regex matching "Super.*"
        where_clause = {"destinations.config.password": {"$regex": "^Super"}}

        response = await self.client.get(
            f"/api/{self.endpoint}", query_string={"where": json.dumps(where_clause)}, headers=self.headers
        )

        self.assertEqual(response.status_code, 400, "Should return 400 Bad Request when filtering by sensitive field")

import json
from superdesk.tests import TestCase, setup_db_user
from superdesk import get_resource_service


class IngestProviderSecurityTestCase(TestCase):
    def setUp(self):
        self.endpoint = "ingest_providers"
        self.service = get_resource_service(self.endpoint)
        self.headers = [("Content-Type", "application/json")]

    async def test_nosql_injection_tokens_regex(self):
        await setup_db_user(self, None)

        # Create an ingest provider with a secret token
        provider_data = {
            "name": "vulnerable_provider",
            "source": "test_source",
            "feeding_service": "http",
            "feed_parser": "json",
            "tokens": {"auth_token": "secrettoken"},
            "config": {"password": "secretpassword"},
        }
        self.service.post([provider_data])

        # Verify provider exists
        resp = await self.client.get(
            f'/api/{self.endpoint}?where={{"name":"vulnerable_provider"}}', headers=self.headers
        )
        self.assertEqual(resp.status_code, 200)
        data = await resp.get_json()
        self.assertEqual(len(data["_items"]), 1)

        # Attempt NoSQL injection to guess token
        where_clause = json.dumps({"name": "vulnerable_provider", "tokens.auth_token": {"$regex": "^secret.*"}})

        resp = await self.client.get(f"/api/{self.endpoint}?where={where_clause}", headers=self.headers)

        # Expect 400 Bad Request
        self.assertEqual(resp.status_code, 400)
        data = await resp.get_json()
        self.assertIn("Filtering by tokens is not allowed", data["_message"])

        # Attempt NoSQL injection to guess config password
        where_clause_config = json.dumps({"name": "vulnerable_provider", "config.password": {"$regex": "^secret.*"}})

        resp = await self.client.get(f"/api/{self.endpoint}?where={where_clause_config}", headers=self.headers)

        # Expect 400 Bad Request
        self.assertEqual(resp.status_code, 400)
        data = await resp.get_json()
        self.assertIn("Filtering by config is not allowed", data["_message"])

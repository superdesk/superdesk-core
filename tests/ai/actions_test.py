# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.ai.service import AIActionsService
from superdesk.tests import TestCase

from .providers_test import ADMIN_USER, PROVIDER, USER_WITHOUT_PRIVILEGES, StubUserAuth

ACTION = {
    "name": "Headline suggestions",
    "action_type": "suggestion",
    "input_fields": ["body_html"],
    "output_field": "headline",
    "max_characters": 60,
}


class AIActionsRestTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._original_auth = self.async_app.auth
        self.async_app.auth = StubUserAuth(ADMIN_USER)
        self.addCleanup(self._restore_auth)
        self.service = AIActionsService()

        response = await self.test_client.post("/api/ai_providers", json=PROVIDER)
        self.assertEqual(response.status_code, 201, await response.get_data())
        self.provider_id = (await response.get_json())["_id"]

    def _restore_auth(self):
        self.async_app.auth = self._original_auth

    def _payload(self, **updates):
        return {**ACTION, "provider": self.provider_id, **updates}

    async def _create_action(self, **updates):
        response = await self.test_client.post("/api/ai_actions", json=self._payload(**updates))
        self.assertEqual(response.status_code, 201, await response.get_data())
        return await response.get_json()

    async def test_action_defaults_are_applied_on_create(self):
        created = await self._create_action()

        action = await self.service.find_by_id(created["_id"])
        self.assertTrue(action.active)
        self.assertEqual(action.suggestions_count, 3)
        self.assertEqual(action.content_profiles, [])
        self.assertIsNone(action.model)
        self.assertEqual(action.parameters.temperature, 0.7)
        self.assertIsNone(action.parameters.system_prompt)

    async def test_action_parameters_are_stored(self):
        created = await self._create_action(parameters={"temperature": 0.2, "system_prompt": "Be brief"})

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.parameters.temperature, 0.2)
        self.assertEqual(action.parameters.system_prompt, "Be brief")

    async def test_action_provider_is_stored_as_the_provider_id(self):
        created = await self._create_action()

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(str(action.provider), self.provider_id)

    async def test_empty_name_is_rejected(self):
        response = await self.test_client.post("/api/ai_actions", json=self._payload(name=""))

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", (await response.get_json())["_issues"])

    async def test_empty_input_fields_is_rejected(self):
        response = await self.test_client.post("/api/ai_actions", json=self._payload(input_fields=[]))

        self.assertEqual(response.status_code, 400)
        self.assertIn("input_fields", (await response.get_json())["_issues"])

    async def test_empty_output_field_is_rejected(self):
        response = await self.test_client.post("/api/ai_actions", json=self._payload(output_field=""))

        self.assertEqual(response.status_code, 400)
        self.assertIn("output_field", (await response.get_json())["_issues"])

    async def test_unknown_action_type_is_rejected(self):
        response = await self.test_client.post("/api/ai_actions", json=self._payload(action_type="proofread"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("action_type", (await response.get_json())["_issues"])

    async def test_suggestions_count_outside_one_to_ten_is_rejected(self):
        for suggestions_count in (0, 11):
            with self.subTest(suggestions_count=suggestions_count):
                response = await self.test_client.post(
                    "/api/ai_actions",
                    json=self._payload(suggestions_count=suggestions_count),
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn("suggestions_count", (await response.get_json())["_issues"])

    async def test_a_provider_that_does_not_exist_is_rejected(self):
        response = await self.test_client.post(
            "/api/ai_actions",
            json=self._payload(provider="6543210987654321098765ab"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("provider", (await response.get_json())["_issues"])

    async def test_a_summary_action_is_created_with_a_single_suggestion(self):
        created = await self._create_action(action_type="summary", suggestions_count=5)

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.suggestions_count, 1)

    async def test_turning_an_action_into_a_summary_drops_it_to_a_single_suggestion(self):
        created = await self._create_action(suggestions_count=5)

        response = await self.test_client.patch(
            f"/api/ai_actions/{created['_id']}",
            json={"action_type": "summary"},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.suggestions_count, 1)

    async def test_a_summary_action_cannot_be_patched_to_several_suggestions(self):
        created = await self._create_action(action_type="summary")

        response = await self.test_client.patch(
            f"/api/ai_actions/{created['_id']}",
            json={"suggestions_count": 4},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.suggestions_count, 1)

    async def test_a_suggestion_action_keeps_the_requested_suggestions_count(self):
        created = await self._create_action(suggestions_count=5)

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.suggestions_count, 5)

    async def test_user_without_the_ai_studio_privilege_cannot_head_actions(self):
        """A HEAD request is answered by the GET handler, so it has to be refused with it"""

        created = await self._create_action()
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        listing = await self.test_client.head("/api/ai_actions")
        item = await self.test_client.head(f"/api/ai_actions/{created['_id']}")

        self.assertEqual(listing.status_code, 403)
        self.assertEqual(item.status_code, 403)

    async def test_user_without_the_ai_studio_privilege_cannot_read_actions(self):
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        response = await self.test_client.get("/api/ai_actions")

        self.assertEqual(response.status_code, 403)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import asyncio
import json
from dataclasses import fields
from unittest.mock import patch

import aiohttp

from superdesk.ai.actions_service import AIActionsService
from superdesk.tests import TestCase
from superdesk.tests.http_mocks import mock_http

from .openai_compatible_test import BASE_URL, COMPLETIONS_URL, capture_requests
from .providers_test import ADMIN_USER, PROVIDER, USER_WITHOUT_PRIVILEGES, StubUserAuth

ACTION = {
    "name": "Headline suggestions",
    "action_type": "suggestion",
    "input_fields": ["body_html"],
    "output_field": "headline",
    "parameters": {"max_characters": 60},
}

ITEM_ID = "urn:newsml:localhost:article-1"

ITEM = {
    "_id": ITEM_ID,
    "guid": ITEM_ID,
    "type": "text",
    "profile": "story",
    "language": "en",
    "headline": "Council meets",
    "body_html": "<p>The council met on Tuesday.</p><p>It voted on the budget.</p>",
}

USER_WITH_AI_PRIVILEGE = {"_id": "test-editor", "user_type": "user", "privileges": {"ai": 1}}
USER_WITH_AI_STUDIO_PRIVILEGE = {"_id": "test-configurator", "user_type": "user", "privileges": {"ai_studio": 1}}


def completion_payload(content: str) -> dict:
    return {
        "model": "gpt-4o-mini-2024-07-18",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 42, "completion_tokens": 7},
    }


SUGGESTIONS_CONTENT = json.dumps({"suggestions": ["Council meets on budget", "Council votes on budget"]})


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
        self.assertEqual(action.parameters.suggestions_count, 3)
        self.assertEqual(action.content_profiles, [])
        self.assertIsNone(action.model)
        self.assertEqual(action.parameters.temperature, 0.7)
        self.assertIsNone(action.parameters.system_prompt)

    async def test_action_parameters_are_stored(self):
        created = await self._create_action(parameters={"temperature": 0.2, "system_prompt": "Be brief"})

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.parameters.temperature, 0.2)
        self.assertEqual(action.parameters.system_prompt, "Be brief")

    async def test_patching_one_parameter_leaves_the_others_alone(self):
        created = await self._create_action(
            parameters={"temperature": 0.2, "system_prompt": "Be brief", "suggestions_count": 5}
        )

        response = await self.test_client.patch(
            f"/api/ai_actions/{created['_id']}",
            json={"parameters": {"temperature": 0.9}},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.parameters.temperature, 0.9)
        self.assertEqual(action.parameters.system_prompt, "Be brief")
        self.assertEqual(action.parameters.suggestions_count, 5)

    async def test_a_parameter_patched_to_null_is_cleared(self):
        created = await self._create_action(parameters={"system_prompt": "Be brief", "max_characters": 60})

        response = await self.test_client.patch(
            f"/api/ai_actions/{created['_id']}",
            json={"parameters": {"system_prompt": None}},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

        action = await self.service.find_by_id(created["_id"])
        self.assertIsNone(action.parameters.system_prompt)
        self.assertEqual(action.parameters.max_characters, 60)

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
                    json=self._payload(parameters={"suggestions_count": suggestions_count}),
                )

                self.assertEqual(response.status_code, 400)
                issues = (await response.get_json())["_issues"]
                self.assertIn("suggestions_count", issues["parameters"])

    async def test_a_provider_that_does_not_exist_is_rejected(self):
        response = await self.test_client.post(
            "/api/ai_actions",
            json=self._payload(provider="6543210987654321098765ab"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("provider", (await response.get_json())["_issues"])

    async def test_a_summary_action_is_created_with_a_single_suggestion(self):
        created = await self._create_action(action_type="summary", parameters={"suggestions_count": 5})

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.parameters.suggestions_count, 1)

    async def test_turning_an_action_into_a_summary_drops_it_to_a_single_suggestion(self):
        created = await self._create_action(parameters={"suggestions_count": 5})

        response = await self.test_client.patch(
            f"/api/ai_actions/{created['_id']}",
            json={"action_type": "summary"},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.parameters.suggestions_count, 1)

    async def test_a_summary_action_cannot_be_patched_to_several_suggestions(self):
        created = await self._create_action(action_type="summary")

        response = await self.test_client.patch(
            f"/api/ai_actions/{created['_id']}",
            json={"parameters": {"suggestions_count": 4}},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.parameters.suggestions_count, 1)

    async def test_a_suggestion_action_keeps_the_requested_suggestions_count(self):
        created = await self._create_action(parameters={"suggestions_count": 5})

        action = await self.service.find_by_id(created["_id"])
        self.assertEqual(action.parameters.suggestions_count, 5)

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


class AIActionRunTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._original_auth = self.async_app.auth
        self.async_app.auth = StubUserAuth(ADMIN_USER)
        self.addCleanup(self._restore_auth)
        self.http_mock = mock_http(self)

        response = await self.test_client.post("/api/ai_providers", json={**PROVIDER, "base_url": BASE_URL})
        self.assertEqual(response.status_code, 201, await response.get_data())
        provider = await response.get_json()
        self.provider_id = provider["_id"]
        self.provider_etag = provider["_etag"]

        await self.async_app.mongo.get_collection_async("archive").insert_one(dict(ITEM))

    def _restore_auth(self):
        self.async_app.auth = self._original_auth

    async def _create_action(self, **updates):
        response = await self.test_client.post(
            "/api/ai_actions",
            json={**ACTION, "provider": self.provider_id, **updates},
        )
        self.assertEqual(response.status_code, 201, await response.get_data())
        return await response.get_json()

    async def _run(self, action_id, **payload):
        return await self.test_client.post(
            f"/api/ai_actions/{action_id}/run",
            json={"item_id": ITEM_ID, **payload},
        )

    async def _run_action(self, content=SUGGESTIONS_CONTENT, action=None, **payload):
        self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(content))
        action = action or await self._create_action()

        response = await self._run(action["_id"], **payload)

        self.assertEqual(response.status_code, 200, await response.get_data())
        return await response.get_json()

    async def _capture_completion(self, content=SUGGESTIONS_CONTENT):
        return capture_requests(self.http_mock, COMPLETIONS_URL, "POST", payload=completion_payload(content))

    async def _capture_run_records(self):
        records = []

        async def record_run(record):
            records.append(record)
            return None

        patcher = patch("superdesk.ai.actions_service.record_run", record_run)
        patcher.start()
        self.addCleanup(patcher.stop)

        return records

    async def test_run_returns_the_suggestions_the_provider_answered_with(self):
        body = await self._run_action()

        self.assertEqual(
            body["suggestions"],
            [
                {"text": "Council meets on budget", "over_limit": False},
                {"text": "Council votes on budget", "over_limit": False},
            ],
        )

    async def test_run_reports_the_provider_the_model_it_answered_with_and_the_token_usage(self):
        body = await self._run_action()

        self.assertEqual(body["provider"], self.provider_id)
        self.assertEqual(body["model"], "gpt-4o-mini-2024-07-18")
        self.assertEqual(body["usage"], {"input_tokens": 42, "output_tokens": 7})

    async def test_the_run_record_identifies_the_item_without_holding_its_text(self):
        records = await self._capture_run_records()

        await self._run_action()

        record = records[0]
        field_names = [field.name for field in fields(record)]
        self.assertNotIn("item", field_names)
        self.assertNotIn(
            "The council met on Tuesday",
            repr([getattr(record, name) for name in field_names]),
        )
        self.assertEqual(record.item_id, ITEM_ID)
        self.assertEqual(record.content_profile, "story")
        self.assertEqual(record.language, "en")
        self.assertEqual(record.input_chars, len("The council met on Tuesday.\nIt voted on the budget."))
        self.assertEqual(record.output_chars, len(SUGGESTIONS_CONTENT))

    async def test_run_asks_for_json_with_the_temperature_and_model_of_the_action(self):
        requests = await self._capture_completion()
        action = await self._create_action(model="openai/gpt-4o", parameters={"temperature": 0.2})

        await self._run(action["_id"])

        self.assertEqual(requests[0]["json"]["model"], "openai/gpt-4o")
        self.assertEqual(requests[0]["json"]["temperature"], 0.2)
        self.assertEqual(requests[0]["json"]["response_format"], {"type": "json_object"})

    async def test_run_falls_back_to_the_default_model_of_the_provider(self):
        requests = await self._capture_completion()
        action = await self._create_action()

        await self._run(action["_id"])

        self.assertEqual(requests[0]["json"]["model"], PROVIDER["default_model"])

    async def test_run_sends_the_item_text_with_the_html_stripped(self):
        requests = await self._capture_completion()
        action = await self._create_action()

        await self._run(action["_id"])

        user_message = requests[0]["json"]["messages"][1]
        self.assertEqual(user_message["role"], "user")
        self.assertEqual(user_message["content"], "The council met on Tuesday.\nIt voted on the budget.")

    async def test_fields_sent_by_the_client_are_used_instead_of_the_stored_item(self):
        requests = await self._capture_completion()
        action = await self._create_action()

        await self._run(action["_id"], fields={"body_html": "<p>An unsaved edit.</p>"})

        self.assertEqual(requests[0]["json"]["messages"][1]["content"], "An unsaved edit.")

    async def test_every_input_field_is_sent_with_its_name_when_the_action_reads_several(self):
        requests = await self._capture_completion()
        action = await self._create_action(input_fields=["headline", "body_html"])

        await self._run(action["_id"])

        self.assertEqual(
            requests[0]["json"]["messages"][1]["content"],
            "headline:\nCouncil meets\n\nbody_html:\nThe council met on Tuesday.\nIt voted on the budget.",
        )

    async def test_the_language_of_the_item_is_asked_for_when_the_payload_has_none(self):
        requests = await self._capture_completion()
        action = await self._create_action()

        await self._run(action["_id"])

        self.assertIn("Write every version in en.", requests[0]["json"]["messages"][0]["content"])

    async def test_the_language_of_the_payload_wins_over_the_language_of_the_item(self):
        requests = await self._capture_completion()
        action = await self._create_action()

        await self._run(action["_id"], language="fi")

        self.assertIn("Write every version in fi.", requests[0]["json"]["messages"][0]["content"])

    async def test_a_suggestion_over_the_character_limit_is_returned_whole_and_flagged(self):
        long_suggestion = "Council votes on the budget after a very long and detailed debate"
        content = json.dumps({"suggestions": [long_suggestion, "Council votes"]})

        body = await self._run_action(content)

        self.assertGreater(len(long_suggestion), ACTION["parameters"]["max_characters"])
        self.assertEqual(
            body["suggestions"],
            [
                {"text": long_suggestion, "over_limit": True},
                {"text": "Council votes", "over_limit": False},
            ],
        )

    async def test_an_answer_that_ignores_the_json_contract_is_read_line_by_line(self):
        body = await self._run_action("- Council meets on budget\n- Council votes on budget")

        self.assertEqual(
            [suggestion["text"] for suggestion in body["suggestions"]],
            ["Council meets on budget", "Council votes on budget"],
        )

    async def test_no_more_suggestions_than_the_action_asks_for_are_returned(self):
        content = json.dumps({"suggestions": ["One", "Two", "Three", "Four"]})

        body = await self._run_action(content, action=await self._create_action(parameters={"suggestions_count": 2}))

        self.assertEqual([suggestion["text"] for suggestion in body["suggestions"]], ["One", "Two"])

    async def test_an_action_limited_to_other_content_profiles_is_rejected(self):
        action = await self._create_action(content_profiles=["gallery"])

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 400)
        self.assertIn("content profile", (await response.get_json())["_message"])

    async def test_an_action_limited_to_the_content_profile_of_the_item_runs(self):
        body = await self._run_action(action=await self._create_action(content_profiles=["story", "gallery"]))

        self.assertEqual(len(body["suggestions"]), 2)

    async def test_an_inactive_action_is_rejected(self):
        action = await self._create_action(active=False)

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 400)
        self.assertIn("not active", (await response.get_json())["_message"])

    async def test_an_action_of_an_inactive_provider_is_rejected(self):
        action = await self._create_action()
        response = await self.test_client.patch(
            f"/api/ai_providers/{self.provider_id}",
            json={"active": False},
            headers={"If-Match": self.provider_etag},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 400)
        self.assertIn("not active", (await response.get_json())["_message"])

    async def test_an_action_whose_provider_was_deleted_is_rejected(self):
        action = await self._create_action()
        response = await self.test_client.delete(
            f"/api/ai_providers/{self.provider_id}",
            headers={"If-Match": self.provider_etag},
        )
        self.assertIn(response.status_code, (200, 204), await response.get_data())

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 400)
        self.assertIn("provider", (await response.get_json())["_message"])
        self.assertIn("no longer exists", (await response.get_json())["_message"])

    async def test_an_item_with_no_text_in_the_input_fields_is_rejected(self):
        action = await self._create_action(input_fields=["abstract"])

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 400)
        self.assertIn("abstract", (await response.get_json())["_message"])

    async def test_input_fields_cleared_by_the_client_are_not_taken_from_the_item(self):
        action = await self._create_action()

        response = await self._run(action["_id"], fields={"body_html": "  "})

        self.assertEqual(response.status_code, 400)
        message = (await response.get_json())["_message"]
        self.assertIn("no text in the fields the action reads", message)
        self.assertIn("body_html", message)

    async def test_an_item_that_does_not_exist_is_not_found(self):
        action = await self._create_action()

        response = await self._run(action["_id"], item_id="urn:newsml:localhost:missing")

        self.assertEqual(response.status_code, 404)

    async def test_an_action_that_does_not_exist_is_not_found(self):
        response = await self._run("6543210987654321098765ab")

        self.assertEqual(response.status_code, 404)

    async def test_a_payload_without_an_item_id_is_rejected(self):
        action = await self._create_action()

        response = await self.test_client.post(f"/api/ai_actions/{action['_id']}/run", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("item_id", (await response.get_json())["_issues"])

    async def test_rewrite_and_translation_are_not_supported_yet(self):
        for action_type in ("rewrite", "translation"):
            with self.subTest(action_type=action_type):
                action = await self._create_action(action_type=action_type)

                response = await self._run(action["_id"])

                self.assertEqual(response.status_code, 400)
                self.assertIn("not supported yet", (await response.get_json())["_message"])

    async def test_a_provider_that_rejects_the_credentials_answers_502(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, status=401)

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(PROVIDER["api_key"], (await response.get_json())["_message"])

    async def test_a_provider_that_rate_limits_answers_429(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, status=429)

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 429)

    async def test_a_provider_that_does_not_answer_in_time_answers_504(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, exception=asyncio.TimeoutError())

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 504)

    async def test_a_provider_that_fails_answers_502(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, status=500)

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 502)

    async def test_a_provider_that_cannot_be_reached_answers_502(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, exception=aiohttp.ClientConnectionError("no route"))

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 502)

    async def test_a_provider_answering_without_a_completion_answers_502(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, payload={"error": "no choices here"})

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 502)

    async def test_a_completion_with_no_text_answers_502_rather_than_no_suggestions(self):
        for content in (None, "   "):
            with self.subTest(content=content):
                action = await self._create_action()
                self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(content))

                response = await self._run(action["_id"])

                self.assertEqual(response.status_code, 502)

    async def test_a_completion_that_is_json_of_an_unreadable_shape_answers_502(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(json.dumps({"result": {"headline": "One"}})))

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 502)

    async def test_a_user_with_only_the_ai_privilege_can_run_an_action(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(SUGGESTIONS_CONTENT))
        self.async_app.auth = StubUserAuth(USER_WITH_AI_PRIVILEGE)

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 200, await response.get_data())

    async def test_a_user_without_the_ai_privilege_cannot_run_an_action(self):
        action = await self._create_action()
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 403)

    async def test_the_ai_studio_privilege_alone_cannot_run_an_action(self):
        """Configuring the actions and running them are separate rights, neither implies the other"""

        action = await self._create_action()
        self.async_app.auth = StubUserAuth(USER_WITH_AI_STUDIO_PRIVILEGE)

        response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 403)

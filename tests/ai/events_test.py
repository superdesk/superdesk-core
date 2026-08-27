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
from unittest.mock import patch

import aiohttp
from bson import ObjectId

from superdesk.ai.errors import AIErrorKind
from superdesk.ai.models import AIActionType, AIEventSource
from superdesk.ai.service import AIActionsService, AIEventsService, AIProvidersService, AIRunRecord, build_event
from superdesk.ai.providers.base import CompletionResult
from superdesk.tests import TestCase
from superdesk.tests.http_mocks import mock_http
from superdesk.utc import utcnow

from .actions_test import ACTION, ITEM, ITEM_ID, SUGGESTIONS_CONTENT, USER_WITH_AI_PRIVILEGE, completion_payload
from .openai_compatible_test import BASE_URL, COMPLETIONS_URL
from .providers_test import ADMIN_USER, PROVIDER, StubUserAuth

DESK_ID = ObjectId("6543210987654321098765ab")

BODY_TEXT = "The council met on Tuesday.\nIt voted on the budget."

#: Distinctive enough to be searched for in whatever the run wrote down
API_KEY = "sk-test-6b41d9-must-never-be-logged"


class AIEventsTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._original_auth = self.async_app.auth
        self.async_app.auth = StubUserAuth(ADMIN_USER)
        self.addCleanup(self._restore_auth)
        self.http_mock = mock_http(self)
        self.events_service = AIEventsService()

        provider = await self._create_provider()
        self.provider_id = provider["_id"]
        self.provider_etag = provider["_etag"]

        await self.async_app.mongo.get_collection_async("archive").insert_one(
            dict(ITEM, task={"desk": DESK_ID, "stage": ObjectId()})
        )

    def _restore_auth(self):
        self.async_app.auth = self._original_auth

    async def _create_provider(self, **updates):
        response = await self.test_client.post(
            "/api/ai_providers",
            json={**PROVIDER, "base_url": BASE_URL, "api_key": API_KEY, **updates},
        )
        self.assertEqual(response.status_code, 201, await response.get_data())
        return await response.get_json()

    async def _deactivate_provider(self, provider):
        response = await self.test_client.patch(
            f"/api/ai_providers/{provider['_id']}",
            json={"active": False},
            headers={"If-Match": provider["_etag"]},
        )
        self.assertEqual(response.status_code, 200, await response.get_data())

    async def _delete_provider(self, provider):
        response = await self.test_client.delete(
            f"/api/ai_providers/{provider['_id']}",
            headers={"If-Match": provider["_etag"]},
        )
        self.assertIn(response.status_code, (200, 204), await response.get_data())

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
        action = action or await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(content))

        response = await self._run(action["_id"], **payload)

        self.assertEqual(response.status_code, 200, await response.get_data())
        return action, await response.get_json()

    async def _stored_events(self):
        return await self.async_app.mongo.get_collection_async("ai_events").find({}).to_list(None)

    async def _single_event(self):
        events = await self._stored_events()
        self.assertEqual(len(events), 1)
        return events[0]

    async def _clear_events(self):
        await self.async_app.mongo.get_collection_async("ai_events").delete_many({})

    async def test_a_successful_run_writes_an_event_describing_the_run(self):
        action, _ = await self._run_action()

        event = await self._single_event()
        self.assertEqual(event["item_id"], ITEM_ID)
        self.assertEqual(event["action_id"], ObjectId(action["_id"]))
        self.assertEqual(event["action_type"], AIActionType.SUGGESTION.value)
        self.assertEqual(event["provider_id"], ObjectId(self.provider_id))
        self.assertEqual(event["provider_type"], PROVIDER["provider_type"])
        self.assertEqual(event["model_requested"], PROVIDER["default_model"])
        self.assertEqual(event["model_reported"], "gpt-4o-mini-2024-07-18")
        self.assertEqual(event["content_profile"], "story")
        self.assertEqual(event["language"], "en")
        self.assertEqual(event["status"], "ok")
        self.assertIsNone(event.get("error_kind"))
        self.assertEqual(event["suggestions"], ["Council meets on budget", "Council votes on budget"])
        self.assertEqual(event["input_chars"], len(BODY_TEXT))
        self.assertEqual(event["output_chars"], len(SUGGESTIONS_CONTENT))
        self.assertEqual(event["prompt_tokens"], 42)
        self.assertEqual(event["completion_tokens"], 7)
        self.assertGreaterEqual(event["latency_ms"], 0)
        self.assertLessEqual(event["requested_at"], event["responded_at"])
        self.assertEqual(event["outcome"], "pending")

    async def test_the_run_response_reports_the_id_of_the_event_it_wrote(self):
        _, body = await self._run_action()

        event = await self._single_event()
        self.assertEqual(body["event_id"], str(event["_id"]))

    async def test_the_event_names_the_user_the_desk_and_the_source_of_the_run(self):
        action = await self._create_action()
        self.async_app.auth = StubUserAuth(USER_WITH_AI_PRIVILEGE)

        await self._run_action(action=action, source="authoring")

        event = await self._single_event()
        self.assertEqual(event["user_id"], USER_WITH_AI_PRIVILEGE["_id"])
        self.assertEqual(event["desk_id"], str(DESK_ID))
        self.assertEqual(event["source"], AIEventSource.AUTHORING.value)

    async def test_the_source_of_a_run_that_does_not_name_one_is_the_api(self):
        await self._run_action()

        event = await self._single_event()
        self.assertEqual(event["source"], AIEventSource.API.value)

    async def test_the_event_holds_neither_the_text_of_the_item_nor_the_provider_key(self):
        await self._run_action()

        event = await self._single_event()
        stored = json.dumps(event, default=str)
        self.assertNotIn(BODY_TEXT, stored)
        self.assertNotIn("The council met on Tuesday", stored)
        self.assertNotIn(API_KEY, stored)
        self.assertEqual(event["input_chars"], len(BODY_TEXT))

    async def test_a_provider_failure_writes_an_event_naming_the_kind_of_failure(self):
        failures = [
            (dict(status=401), AIErrorKind.AUTH, 502),
            (dict(status=429), AIErrorKind.RATE_LIMIT, 429),
            (dict(status=500), AIErrorKind.UPSTREAM, 502),
            (dict(exception=asyncio.TimeoutError()), AIErrorKind.TIMEOUT, 504),
            (dict(exception=aiohttp.ClientConnectionError("no route")), AIErrorKind.UPSTREAM, 502),
        ]

        for answer, error_kind, status_code in failures:
            with self.subTest(error_kind=error_kind):
                await self._clear_events()
                action = await self._create_action()
                self.http_mock.post(COMPLETIONS_URL, **answer)

                response = await self._run(action["_id"])

                self.assertEqual(response.status_code, status_code, await response.get_data())
                event = await self._single_event()
                self.assertEqual(event["status"], "error")
                self.assertEqual(event["error_kind"], error_kind.value)
                self.assertEqual(event["suggestions"], [])
                self.assertEqual(event["output_chars"], 0)
                self.assertIsNone(event.get("model_reported"))
                self.assertEqual(event["input_chars"], len(BODY_TEXT))

    async def test_a_completion_that_cannot_be_read_writes_an_event_with_an_invalid_response(self):
        contents = ["   ", json.dumps({"result": {"headline": "One"}})]

        for content in contents:
            with self.subTest(content=content):
                await self._clear_events()
                action = await self._create_action()
                self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(content))

                response = await self._run(action["_id"])

                self.assertEqual(response.status_code, 502)
                event = await self._single_event()
                self.assertEqual(event["status"], "error")
                self.assertEqual(event["error_kind"], AIErrorKind.INVALID_RESPONSE.value)
                self.assertEqual(event["suggestions"], [])
                self.assertEqual(event["output_chars"], len(content))

    async def test_a_run_rejected_before_the_provider_is_called_writes_no_event(self):
        rejections = [
            (dict(active=False), dict()),
            (dict(content_profiles=["gallery"]), dict()),
            (dict(input_fields=["abstract"]), dict()),
            (dict(), dict(item_id="urn:newsml:localhost:missing")),
        ]

        for action_updates, payload in rejections:
            with self.subTest(action_updates=action_updates, payload=payload):
                action = await self._create_action(**action_updates)

                response = await self._run(action["_id"], **payload)

                self.assertIn(response.status_code, (400, 404), await response.get_data())
                self.assertEqual(await self._stored_events(), [])

    async def test_a_run_rejected_over_its_provider_writes_no_event(self):
        """A provider a stored action points at can stop being usable long after the action was saved"""

        rejections = [
            (dict(default_model=None), None, "no model"),
            (dict(), self._deactivate_provider, "not active"),
            (dict(), self._delete_provider, "no longer exists"),
        ]

        for provider_fields, break_provider, message in rejections:
            with self.subTest(rejection=message):
                provider = await self._create_provider(name=message, **provider_fields)
                action = await self._create_action(provider=provider["_id"])
                if break_provider is not None:
                    await break_provider(provider)

                response = await self._run(action["_id"])

                self.assertEqual(response.status_code, 400, await response.get_data())
                self.assertIn(message, (await response.get_json())["_message"])
                self.assertEqual(await self._stored_events(), [])

    async def test_a_failing_event_write_does_not_fail_the_run(self):
        self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(SUGGESTIONS_CONTENT))
        action = await self._create_action()

        with patch.object(AIEventsService, "create", side_effect=RuntimeError("mongo is down")):
            response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 200, await response.get_data())
        body = await response.get_json()
        self.assertEqual(len(body["suggestions"]), 2)
        self.assertIsNone(body["event_id"])

    async def test_a_failing_event_write_does_not_hide_a_provider_failure(self):
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, status=401)

        with patch.object(AIEventsService, "create", side_effect=RuntimeError("mongo is down")):
            response = await self._run(action["_id"])

        self.assertEqual(response.status_code, 502, await response.get_data())
        self.assertEqual(await self._stored_events(), [])

    async def test_an_event_that_cannot_be_built_does_not_fail_the_run_either(self):
        """The log is written from the item as stored, which nothing validates on the way in"""

        item_id = "urn:newsml:localhost:article-2"
        # ``AIEvent.language`` is a string, so an item holding a list there cannot be turned into an
        # event at all, before any write is attempted
        await self.async_app.mongo.get_collection_async("archive").insert_one(
            dict(ITEM, _id=item_id, guid=item_id, language=["en"])
        )
        action = await self._create_action()
        self.http_mock.post(COMPLETIONS_URL, payload=completion_payload(SUGGESTIONS_CONTENT))

        response = await self._run(action["_id"], item_id=item_id)

        self.assertEqual(response.status_code, 200, await response.get_data())
        body = await response.get_json()
        self.assertEqual(len(body["suggestions"]), 2)
        self.assertIsNone(body["event_id"])
        self.assertEqual(await self._stored_events(), [])

    async def test_the_answers_of_a_long_output_action_type_are_not_kept_on_the_event(self):
        created = await self._create_action(action_type=AIActionType.REWRITE.value)
        action = await AIActionsService().find_by_id(created["_id"])
        provider = await AIProvidersService().find_by_id(self.provider_id)
        assert action is not None and provider is not None
        now = utcnow()

        event = build_event(
            AIRunRecord(
                action=action,
                provider=provider,
                item_id=ITEM_ID,
                model_requested="gpt-4o-mini",
                requested_at=now,
                responded_at=now,
                input_chars=10,
                result=CompletionResult(content="A whole rewritten article", model="gpt-4o-mini"),
                suggestions=["A whole rewritten article"],
            )
        )

        self.assertEqual(event.suggestions, [])
        self.assertEqual(event.output_chars, len("A whole rewritten article"))

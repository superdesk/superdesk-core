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
from datetime import timezone
from unittest.mock import patch

import aiohttp
from bson import ObjectId

from superdesk.ai.actions_service import AIActionsService
from superdesk.ai.errors import AIErrorKind
from superdesk.ai.events_service import AIEventsService, AIRunRecord, build_event
from superdesk.ai.models import AIActionType, AIEventSource
from superdesk.ai.providers.base import CompletionResult
from superdesk.ai.providers_service import AIProvidersService
from superdesk.tests import TestCase
from superdesk.tests.http_mocks import mock_http
from superdesk.utc import utcnow

from .actions_test import (
    ACTION,
    ITEM,
    ITEM_ID,
    SUGGESTIONS_CONTENT,
    USER_WITH_AI_PRIVILEGE,
    USER_WITH_AI_STUDIO_PRIVILEGE,
    completion_payload,
)
from .openai_compatible_test import BASE_URL, COMPLETIONS_URL
from .providers_test import ADMIN_USER, PROVIDER, USER_WITHOUT_PRIVILEGES, StubUserAuth

DESK_ID = ObjectId("6543210987654321098765ab")

BODY_TEXT = "The council met on Tuesday.\nIt voted on the budget."

#: Distinctive enough to be searched for in whatever the run wrote down
API_KEY = "sk-test-6b41d9-must-never-be-logged"

OTHER_AI_USER = {"_id": "test-other-editor", "user_type": "user", "privileges": {"ai": 1}}
AI_STUDIO_USER = {"_id": "test-supervisor", "user_type": "user", "privileges": {"ai": 1, "ai_studio": 1}}


class AIRunLogTestCase(TestCase):
    """Base for the event tests: a provider, an item on a desk, and the run helpers"""

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


class AIEventsTestCase(AIRunLogTestCase):
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
        self.assertEqual(event["input_tokens"], 42)
        self.assertEqual(event["output_tokens"], 7)
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

    async def test_the_event_log_lists_the_runs_that_were_made(self):
        _, body = await self._run_action()

        response = await self.test_client.get("/api/ai_events")

        self.assertEqual(response.status_code, 200, await response.get_data())
        listed = (await response.get_json())["_items"]
        self.assertEqual([event["_id"] for event in listed], [body["event_id"]])

    async def test_reading_the_event_log_requires_the_ai_studio_privilege(self):
        await self._run_action()
        self.async_app.auth = StubUserAuth(USER_WITH_AI_PRIVILEGE)

        listing = await self.test_client.get("/api/ai_events")
        item = await self.test_client.get(f"/api/ai_events/{(await self._single_event())['_id']}")

        self.assertEqual(listing.status_code, 403)
        self.assertEqual(item.status_code, 403)

    async def test_heading_the_event_log_requires_the_ai_studio_privilege(self):
        """A HEAD request is answered by the GET handler, including the one behind a ``where``"""

        await self._run_action()
        urls = [
            "/api/ai_events",
            "/api/ai_events?where=" + json.dumps({"status": "ok"}),
            f"/api/ai_events/{(await self._single_event())['_id']}",
        ]

        for user in (USER_WITHOUT_PRIVILEGES, USER_WITH_AI_PRIVILEGE):
            self.async_app.auth = StubUserAuth(user)

            for url in urls:
                with self.subTest(user=user["_id"], url=url):
                    response = await self.test_client.head(url)

                    self.assertEqual(response.status_code, 403)


class AIEventOutcomeTestCase(AIRunLogTestCase):
    """The outcome a client reports once it knows what was done with the answers of a run"""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.action = await self._create_action()
        # The run, and every report about it, is made by the editor it belongs to. The base class
        # authenticates as an administrator because creating the action needs ``ai_studio``.
        self.async_app.auth = StubUserAuth(USER_WITH_AI_PRIVILEGE)
        _, self.run_body = await self._run_action(action=self.action)
        self.event_id = self.run_body["event_id"]

    async def _patch(self, updates):
        return await self.test_client.patch(f"/api/ai_events/{self.event_id}", json=updates)

    async def test_reporting_an_outcome_needs_no_etag_the_client_cannot_read(self):
        read = await self.test_client.get(f"/api/ai_events/{self.event_id}")
        reported = await self.test_client.patch(f"/api/ai_events/{self.event_id}", json={"outcome": "accepted"})

        self.assertEqual(read.status_code, 403)
        self.assertEqual(reported.status_code, 200, await reported.get_data())

    async def test_reporting_an_outcome_stores_it_with_the_index_that_was_applied(self):
        response = await self._patch({"outcome": "accepted", "applied_index": 1})

        self.assertEqual(response.status_code, 200, await response.get_data())
        event = await self._single_event()
        self.assertEqual(event["outcome"], "accepted")
        self.assertEqual(event["applied_index"], 1)

    async def test_every_reportable_outcome_is_accepted(self):
        for outcome in ("accepted", "edited", "discarded"):
            with self.subTest(outcome=outcome):
                response = await self._patch({"outcome": outcome})

                self.assertEqual(response.status_code, 200, await response.get_data())
                self.assertEqual((await self._single_event())["outcome"], outcome)

    async def test_an_outcome_outside_the_vocabulary_is_rejected(self):
        response = await self._patch({"outcome": "ignored"})

        self.assertEqual(response.status_code, 400)

    async def test_an_event_cannot_be_reported_back_to_pending(self):
        accepted = await self._patch({"outcome": "accepted"})
        self.assertEqual(accepted.status_code, 200, await accepted.get_data())

        response = await self._patch({"outcome": "pending"})

        self.assertEqual(response.status_code, 400, await response.get_data())
        self.assertIn("pending", (await response.get_json())["_message"])
        self.assertEqual((await self._single_event())["outcome"], "accepted")

    async def test_a_second_report_replaces_the_outcome_of_the_first(self):
        first = await self._patch({"outcome": "accepted", "applied_index": 0})
        self.assertEqual(first.status_code, 200, await first.get_data())

        second = await self._patch({"outcome": "edited"})

        self.assertEqual(second.status_code, 200, await second.get_data())
        event = await self._single_event()
        self.assertEqual(event["outcome"], "edited")
        self.assertEqual(event["applied_index"], 0)

    async def test_a_report_that_no_answer_was_used_clears_the_index_of_the_previous_one(self):
        accepted = await self._patch({"outcome": "accepted", "applied_index": 0})
        self.assertEqual(accepted.status_code, 200, await accepted.get_data())

        discarded = await self._patch({"outcome": "discarded"})

        self.assertEqual(discarded.status_code, 200, await discarded.get_data())
        event = await self._single_event()
        self.assertEqual(event["outcome"], "discarded")
        self.assertIsNone(event["applied_index"])

    async def test_an_applied_index_that_names_no_answer_of_the_run_is_rejected(self):
        rejections = [
            ({"outcome": "accepted", "applied_index": 2}, "names none of the 2 suggestions"),
            ({"outcome": "accepted", "applied_index": -1}, "names none of the 2 suggestions"),
            ({"outcome": "discarded", "applied_index": 0}, "belongs to an outcome of 'accepted' or 'edited'"),
        ]

        for updates, message in rejections:
            with self.subTest(updates=updates):
                response = await self._patch(updates)

                self.assertEqual(response.status_code, 400, await response.get_data())
                self.assertIn(message, (await response.get_json())["_message"])
                self.assertEqual((await self._single_event())["outcome"], "pending")

    async def test_an_applied_index_cannot_be_reported_for_a_run_that_produced_no_answers(self):
        await self._clear_events()
        self.http_mock.post(COMPLETIONS_URL, status=401)
        failed = await self._run(self.action["_id"])
        self.assertEqual(failed.status_code, 502, await failed.get_data())
        event_id = (await self._single_event())["_id"]

        response = await self.test_client.patch(
            f"/api/ai_events/{event_id}",
            json={"outcome": "accepted", "applied_index": 0},
        )

        self.assertEqual(response.status_code, 400, await response.get_data())
        self.assertIn("names none of the 0 suggestions", (await response.get_json())["_message"])

    async def test_the_answer_to_a_report_carries_the_outcome_and_nothing_else(self):
        response = await self._patch({"outcome": "accepted", "applied_index": 1})

        self.assertEqual(response.status_code, 200, await response.get_data())
        body = await response.get_json()
        self.assertEqual(set(body), {"_id", "outcome", "applied_index", "outcome_at"})
        self.assertEqual(body["_id"], self.event_id)
        self.assertEqual(body["outcome"], "accepted")
        self.assertEqual(body["applied_index"], 1)
        self.assertTrue(body["outcome_at"])

    async def test_the_server_stamps_the_time_the_outcome_was_reported(self):
        before = utcnow()

        response = await self._patch({"outcome": "discarded"})

        self.assertEqual(response.status_code, 200, await response.get_data())
        outcome_at = (await self._single_event())["outcome_at"].replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(outcome_at, before.replace(microsecond=0))
        self.assertLessEqual(outcome_at, utcnow())

    async def test_the_time_the_outcome_was_reported_cannot_be_sent_by_the_client(self):
        response = await self._patch({"outcome": "accepted", "outcome_at": "2020-01-01T00:00:00+0000"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("outcome_at", (await response.get_json())["_message"])
        self.assertEqual((await self._single_event())["outcome"], "pending")

    async def test_no_field_of_the_run_itself_can_be_updated(self):
        run_fields = [
            {"suggestions": ["Rewritten by the client"]},
            {"status": "error"},
            {"error_kind": "auth"},
            {"item_id": "urn:newsml:localhost:another"},
            {"input_chars": 0},
            {"user_id": "someone-else"},
        ]

        for updates in run_fields:
            with self.subTest(updates=updates):
                response = await self._patch(updates)

                self.assertEqual(response.status_code, 400, await response.get_data())
                self.assertIn(next(iter(updates)), (await response.get_json())["_message"])

    async def test_a_field_that_is_not_on_the_event_is_rejected(self):
        response = await self._patch({"comment": "looked good"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("comment", (await response.get_json())["_message"])

    async def test_the_user_a_run_was_made_for_can_report_its_outcome(self):
        response = await self._patch({"outcome": "accepted"})

        self.assertEqual(response.status_code, 200, await response.get_data())
        self.assertEqual((await self._single_event())["outcome"], "accepted")

    async def test_another_user_cannot_report_the_outcome_of_a_run_that_is_not_theirs(self):
        self.async_app.auth = StubUserAuth(OTHER_AI_USER)

        response = await self._patch({"outcome": "accepted"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual((await self._single_event())["outcome"], "pending")

    async def test_a_user_who_can_read_the_log_can_report_on_a_run_of_anyone(self):
        reports = [(AI_STUDIO_USER, "accepted"), (ADMIN_USER, "edited")]

        for user, outcome in reports:
            with self.subTest(user=user["_id"]):
                self.async_app.auth = StubUserAuth(user)

                response = await self._patch({"outcome": outcome})

                self.assertEqual(response.status_code, 200, await response.get_data())
                self.assertEqual((await self._single_event())["outcome"], outcome)

    async def test_a_user_without_the_ai_privilege_cannot_report_an_outcome(self):
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        response = await self._patch({"outcome": "accepted"})

        self.assertEqual(response.status_code, 403)

    async def test_the_ai_studio_privilege_alone_cannot_report_an_outcome(self):
        """Reading the whole log widens which entries may be reported on, it does not replace ``ai``"""

        self.async_app.auth = StubUserAuth(USER_WITH_AI_STUDIO_PRIVILEGE)

        response = await self._patch({"outcome": "accepted"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual((await self._single_event())["outcome"], "pending")

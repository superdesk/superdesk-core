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
import socket
import time
from unittest.mock import patch

from bson import ObjectId

from superdesk.ai.config import config
from superdesk.tests import TestCase
from superdesk.tests.http_mocks import mock_http

from .actions_test import ACTION, ITEM, ITEM_ID, completion_payload
from .openai_compatible_test import BASE_URL, COMPLETIONS_URL, capture_requests
from .providers_test import ADMIN_USER, PROVIDER, StubUserAuth

#: 30 seconds into a minute, so a refused run is told to retry in 30 seconds
NOW = 1_800_000_030.0

CONTENT = json.dumps({"suggestions": ["Council meets on budget"]})


class AIRunRateLimitTestCase(TestCase):
    app_config = {"AI_RATE_LIMIT_PER_MINUTE": 2}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._original_auth = self.async_app.auth
        self.async_app.auth = StubUserAuth(ADMIN_USER)
        self.addCleanup(self._restore_auth)
        self.http_mock = mock_http(self)
        self.requests = capture_requests(
            self.http_mock, COMPLETIONS_URL, "POST", repeat=True, payload=completion_payload(CONTENT)
        )

        response = await self.test_client.post("/api/ai_providers", json={**PROVIDER, "base_url": BASE_URL})
        self.assertEqual(response.status_code, 201, await response.get_data())
        response = await self.test_client.post(
            "/api/ai_actions", json={**ACTION, "provider": (await response.get_json())["_id"]}
        )
        self.assertEqual(response.status_code, 201, await response.get_data())
        self.action_id = (await response.get_json())["_id"]

        await self.async_app.mongo.get_collection_async("archive").insert_one(dict(ITEM))

        self.now = NOW
        clock = patch("superdesk.ai.rate_limit._now", side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

        # Counts live in Redis, which is not reset between tests, so every test runs as its own user
        self._sign_in_as_new_editor()

    def _restore_auth(self):
        self.async_app.auth = self._original_auth

    def _sign_in_as_new_editor(self):
        self.async_app.auth = StubUserAuth({"_id": str(ObjectId()), "user_type": "user", "privileges": {"ai": 1}})

    async def _run(self):
        return await self.test_client.post(f"/api/ai_actions/{self.action_id}/run", json={"item_id": ITEM_ID})

    async def _run_times(self, count):
        for _ in range(count):
            response = await self._run()
            self.assertEqual(response.status_code, 200, await response.get_data())

    async def test_a_run_over_the_limit_is_refused_without_calling_the_provider(self):
        await self._run_times(2)

        response = await self._run()
        body = await response.get_json()

        self.assertEqual(response.status_code, 429)
        self.assertEqual(body["error_kind"], "too_many_runs")
        self.assertEqual(body["retry_after"], 30)
        self.assertEqual(response.headers["Retry-After"], "30")
        self.assertIn("30 seconds", body["_message"])
        self.assertEqual(len(self.requests), 2)

    async def test_the_wait_before_a_retry_is_rounded_up_to_reach_the_next_minute(self):
        self.now = NOW + 0.5
        await self._run_times(2)

        response = await self._run()

        self.assertEqual((await response.get_json())["retry_after"], 30)
        self.assertEqual(response.headers["Retry-After"], "30")

    async def test_a_refused_run_is_not_written_to_the_run_log(self):
        await self._run_times(2)

        await self._run()

        events = await self.async_app.mongo.get_collection_async("ai_events").count_documents({})
        self.assertEqual(events, 2)

    async def test_the_limit_is_counted_per_user(self):
        await self._run_times(2)

        self._sign_in_as_new_editor()

        await self._run_times(1)

    async def test_the_count_starts_again_the_next_minute(self):
        await self._run_times(2)

        self.now += 60

        await self._run_times(1)

    async def test_no_limit_is_enforced_when_set_to_zero(self):
        with patch.object(config, "rate_limit_per_minute", 0):
            await self._run_times(3)

    async def test_runs_are_not_blocked_when_redis_cannot_be_reached(self):
        # A port nothing listens on, so connecting is refused
        with socket.socket() as unused:
            unused.bind(("127.0.0.1", 0))
            port = unused.getsockname()[1]

        with patch.dict(self.app.config, {"REDIS_URL": f"redis://127.0.0.1:{port}/0"}):
            await self._run_times(3)

    async def test_runs_are_not_blocked_when_redis_stops_answering(self):
        # Takes connections and never answers them, like a Redis that hangs
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen()
        self.addCleanup(server.close)
        url = "redis://127.0.0.1:{}/0".format(server.getsockname()[1])

        started = time.monotonic()
        with patch.dict(self.app.config, {"REDIS_URL": url}):
            await asyncio.wait_for(self._run_times(3), timeout=20)

        self.assertLess(time.monotonic() - started, 10)

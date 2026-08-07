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
import unittest
from unittest import mock

import aiohttp
from bson import ObjectId
from celery.exceptions import Retry

from superdesk.tests import TestCase

from apps.content_lists.webhooks import (
    WEBHOOK_RETRY_COUNTDOWN,
    ContentListWebhooksService,
    WebhookContentListDelivery,
    deliver_content_list_webhook,
    enqueue_webhook_deliveries,
)


class ContentListWebhookDeliveryTestCase(unittest.IsolatedAsyncioTestCase):
    """Unit tests for the outbound delivery task (no app context needed)."""

    async def test_objectid_payload_is_serialized_to_string(self):
        # The Celery serializer re-casts hex-string ids back into ObjectId on the
        # worker, so the task receives an ObjectId here. Encoding must not raise
        # and must render it as its hex string. Regression for the original
        # "Object of type ObjectId is not JSON serializable" failure.
        list_id = ObjectId("6a0ce307233d76adba4d8ca8")
        payload = {"event": "content_list:items_updated", "list_id": list_id}

        response_mock = mock.MagicMock()
        post_context = mock.MagicMock()
        post_context.__aenter__ = mock.AsyncMock(return_value=response_mock)
        post_context.__aexit__ = mock.AsyncMock(return_value=False)
        session_mock = mock.MagicMock()
        session_mock.post = mock.MagicMock(return_value=post_context)

        with mock.patch.object(WebhookContentListDelivery, "http_session", mock.AsyncMock(return_value=session_mock)):
            await deliver_content_list_webhook.run("https://example.com/hook", payload)

        session_mock.post.assert_called_once()
        args, kwargs = session_mock.post.call_args
        self.assertEqual(args[0], "https://example.com/hook")
        body = json.loads(kwargs["data"])
        self.assertEqual(body["list_id"], str(list_id))
        self.assertEqual(body["event"], "content_list:items_updated")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        response_mock.raise_for_status.assert_called_once()


class ContentListWebhookRetryTestCase(unittest.IsolatedAsyncioTestCase):
    """Retry behaviour of the delivery task on network failures."""

    async def _run_with_failure(self, exc, retries):
        """Run the task with post_list failing; return (raised Retry or None, retry mock)."""
        with (
            mock.patch.object(WebhookContentListDelivery, "post_list", mock.AsyncMock(side_effect=exc)),
            mock.patch.object(deliver_content_list_webhook, "retry", side_effect=Retry("retrying")) as retry_mock,
        ):
            deliver_content_list_webhook.push_request(retries=retries)
            raised = None
            try:
                await deliver_content_list_webhook.run("https://example.com/hook", {"event": "e"})
            except Retry as retry_exc:
                raised = retry_exc
            finally:
                deliver_content_list_webhook.pop_request()
        return raised, retry_mock

    async def test_client_error_triggers_retry_with_countdown(self):
        exc = aiohttp.ClientError("connection refused")
        raised, retry_mock = await self._run_with_failure(exc, retries=0)
        self.assertIsNotNone(raised)
        retry_mock.assert_called_once()
        self.assertEqual(retry_mock.call_args.kwargs["countdown"], WEBHOOK_RETRY_COUNTDOWN)
        self.assertIs(retry_mock.call_args.kwargs["exc"], exc)

    async def test_timeout_error_triggers_retry(self):
        raised, retry_mock = await self._run_with_failure(asyncio.TimeoutError(), retries=0)
        self.assertIsNotNone(raised)
        retry_mock.assert_called_once()

    async def test_gives_up_after_max_retries_and_logs(self):
        exc = aiohttp.ClientError("still failing")
        with (
            mock.patch.object(WebhookContentListDelivery, "post_list", mock.AsyncMock(side_effect=exc)),
            mock.patch.object(deliver_content_list_webhook, "retry", side_effect=Retry("retrying")) as retry_mock,
            self.assertLogs("apps.content_lists.webhooks", level="ERROR") as logs,
        ):
            deliver_content_list_webhook.push_request(retries=deliver_content_list_webhook.max_retries)
            try:
                await deliver_content_list_webhook.run("https://example.com/hook", {"event": "e"})
            finally:
                deliver_content_list_webhook.pop_request()

        retry_mock.assert_not_called()
        self.assertIn("failed after", logs.output[0])

    async def test_non_retryable_exception_propagates(self):
        with mock.patch.object(
            WebhookContentListDelivery, "post_list", mock.AsyncMock(side_effect=ValueError("bad payload"))
        ):
            deliver_content_list_webhook.push_request(retries=0)
            try:
                with self.assertRaises(ValueError):
                    await deliver_content_list_webhook.run("https://example.com/hook", {"event": "e"})
            finally:
                deliver_content_list_webhook.pop_request()


class ContentListWebhookEnqueueTestCase(TestCase):
    """The enqueue step only dispatches to enabled, non-excluded webhooks."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.list_id = ObjectId()
        self.service = ContentListWebhooksService()
        await self.service.create(
            [
                {"url": "https://enabled.example.com", "enabled": True},
                {"url": "https://disabled.example.com", "enabled": False},
                {
                    "url": "https://excluded.example.com",
                    "enabled": True,
                    "excluded_lists": [self.list_id],
                },
            ]
        )

    async def test_only_enabled_and_not_excluded_are_dispatched(self):
        with mock.patch.object(
            deliver_content_list_webhook, "apply_async", new_callable=mock.AsyncMock
        ) as apply_async_mock:
            await enqueue_webhook_deliveries("content_list:items_updated", self.list_id)

        self.assertEqual(apply_async_mock.await_count, 1)
        kwargs = apply_async_mock.await_args.kwargs["kwargs"]
        # URLs are stored WHATWG-canonicalized, so the bare domain entered in
        # setUp gains a trailing slash.
        self.assertEqual(kwargs["url"], "https://enabled.example.com/")
        self.assertEqual(kwargs["payload"]["list_id"], str(self.list_id))
        self.assertEqual(kwargs["payload"]["event"], "content_list:items_updated")


class ContentListWebhookEnqueueNeverRaisesTestCase(TestCase):
    """enqueue_webhook_deliveries must never fail the triggering request."""

    async def test_swallows_webhook_lookup_errors(self):
        with (
            mock.patch.object(
                ContentListWebhooksService, "get_all_list", mock.AsyncMock(side_effect=RuntimeError("db down"))
            ),
            self.assertLogs("apps.content_lists.webhooks", level="ERROR") as logs,
        ):
            await enqueue_webhook_deliveries("content_list:updated", ObjectId())
        self.assertIn("Failed to enqueue", logs.output[0])

    async def test_swallows_apply_async_errors(self):
        await ContentListWebhooksService().create([{"url": "https://enabled.example.com", "enabled": True}])
        with (
            mock.patch.object(
                deliver_content_list_webhook,
                "apply_async",
                new_callable=mock.AsyncMock,
                side_effect=RuntimeError("broker down"),
            ),
            self.assertLogs("apps.content_lists.webhooks", level="ERROR") as logs,
        ):
            await enqueue_webhook_deliveries("content_list:updated", ObjectId())
        self.assertIn("Failed to enqueue", logs.output[0])

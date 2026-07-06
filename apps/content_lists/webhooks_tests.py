# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import unittest
from unittest import mock

from bson import ObjectId

from superdesk.tests import TestCase

from apps.content_lists.webhooks import (
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

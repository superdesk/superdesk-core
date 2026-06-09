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
    deliver_content_list_webhook,
    enqueue_webhook_deliveries,
)


class ContentListWebhookDeliveryTestCase(unittest.TestCase):
    """Unit tests for the outbound delivery task (no app context needed)."""

    @mock.patch("apps.content_lists.webhooks.requests.post")
    def test_objectid_payload_is_serialized_to_string(self, post_mock):
        # The Celery serializer re-casts hex-string ids back into ObjectId on the
        # worker, so the task receives an ObjectId here. Encoding must not raise
        # and must render it as its hex string. Regression for the original
        # "Object of type ObjectId is not JSON serializable" failure.
        list_id = ObjectId("6a0ce307233d76adba4d8ca8")
        payload = {"event": "content_list:items_updated", "list_id": list_id}

        deliver_content_list_webhook.run("https://example.com/hook", payload)

        post_mock.assert_called_once()
        body = json.loads(post_mock.call_args.kwargs["data"])
        self.assertEqual(body["list_id"], str(list_id))
        self.assertEqual(body["event"], "content_list:items_updated")
        self.assertEqual(
            post_mock.call_args.kwargs["headers"]["Content-Type"], "application/json"
        )


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
        self.assertEqual(kwargs["url"], "https://enabled.example.com")
        self.assertEqual(kwargs["payload"]["list_id"], str(self.list_id))
        self.assertEqual(kwargs["payload"]["event"], "content_list:items_updated")

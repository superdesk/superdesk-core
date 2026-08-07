import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from superdesk.tests import TestCase
from superdesk.resource_fields import VERSION
from superdesk.types import PublishState
from superdesk.publish_async.exchanges.content_exchange import ContentPublishExchange
from superdesk.publish_async.utils import QUEUE_STATE, PUBLISHED


class ContentExchangeCancelledErrorTestCase(TestCase):
    """
    Tests that asyncio.CancelledError (a BaseException, not Exception) during
    _publish_item() does not leave published.queue_state permanently stuck at
    in_progress. The handler should reset the item to ``pending`` and clean up
    any incomplete publish_queue rows for the same item/version.
    """

    def _make_exchange(self):
        exchange = ContentPublishExchange.__new__(ContentPublishExchange)
        exchange._filter = MagicMock()
        exchange._formatter = MagicMock()
        exchange._router = MagicMock()
        exchange.polling = False
        return exchange

    async def test_has_publish_queue_items_checks_any_existing_row_for_item_version(self):
        exchange = self._make_exchange()

        request = MagicMock()
        request.item = {VERSION: 7}
        request.item_id = "test-item-1"

        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[{"state": "failed"}])

        queue_service = MagicMock()
        queue_service.find = AsyncMock(return_value=cursor)

        with patch(
            "superdesk.publish_async.exchanges.content_exchange.PublishQueueResource.get_service",
            return_value=queue_service,
        ):
            has_queue_items = await exchange._has_publish_queue_items(request)

        self.assertTrue(has_queue_items)
        queue_service.find.assert_awaited_once_with(
            {
                "$and": [
                    {"item_id": "test-item-1"},
                    {"item_version": 7},
                    {
                        "state": {
                            "$in": [
                                "routing",
                                "pending",
                                "in-progress",
                                "retrying",
                            ]
                        }
                    },
                ]
            },
            max_results=1,
        )

    async def test_cancellation_cleanup_still_updates_state_when_cleanup_await_is_cancelled(self):
        exchange = self._make_exchange()

        published_service = MagicMock()
        published_service.patch_async = AsyncMock()
        request = MagicMock()
        request.item = {"version": 7}
        request.item_id = "test-item-1"
        request.operation = "publish"

        lookup_started = asyncio.Event()
        finish_lookup = asyncio.Event()

        async def delayed_updates(*args, **kwargs):
            lookup_started.set()
            await finish_lookup.wait()
            return {QUEUE_STATE: PublishState.PENDING, "error_message": "request cancelled"}

        async def run_cleanup():
            await exchange._reset_published_item_after_cancellation(
                published_service,
                ObjectId(),
                request,
                asyncio.CancelledError("request cancelled"),
                MagicMock(),
                "Publish request cancelled during routing",
            )

        with patch.object(exchange, "_get_cancellation_error_updates", side_effect=delayed_updates):
            cleanup_await = asyncio.create_task(run_cleanup())
            await lookup_started.wait()

            cleanup_await.cancel()
            await cleanup_await

            finish_lookup.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        published_service.patch_async.assert_awaited_once()

    async def test_cancellation_resets_queue_state_to_pending_when_no_queue_items_exist(self):
        exchange = self._make_exchange()

        published_item_id = ObjectId()
        published_item = {
            "_id": published_item_id,
            "item_id": "test-item-1",
            "state": "published",
            "queue_state": "in_progress",
            "type": "text",
            "operation": "publish",
        }

        captured_patches = []

        async def fake_patch(item_id, updates):
            captured_patches.append((item_id, updates.copy()))

        published_service = MagicMock()
        published_service.patch_async = AsyncMock(side_effect=fake_patch)

        request = MagicMock()
        request.item = MagicMock(**published_item)  # wrap dict so .get() can be mocked
        request.item.get = MagicMock(return_value=None)  # not SCHEDULED
        request.item_id = "test-item-1"
        request.operation = "publish"

        with patch(
            "superdesk.publish_async.exchanges.content_exchange.PublishCache.init",
            new_callable=AsyncMock,
        ):
            with patch(
                "superdesk.publish_async.exchanges.content_exchange.get_resource_service",
                return_value=published_service,
            ):
                with patch.object(
                    exchange,
                    "get_published_item_from_request",
                    new_callable=AsyncMock,
                    return_value=published_item,
                ):
                    with patch.object(
                        exchange,
                        "update_published_item",
                        new_callable=AsyncMock,
                    ):
                        with patch.object(
                            exchange,
                            "_has_publish_queue_items",
                            new_callable=AsyncMock,
                            return_value=False,
                        ):
                            with patch.object(
                                exchange,
                                "_publish_item",
                                new_callable=AsyncMock,
                                side_effect=asyncio.CancelledError("request cancelled"),
                            ):
                                with self.assertRaises(asyncio.CancelledError):
                                    await exchange.send(request)

        # The BaseException handler must have written a state reset
        self.assertTrue(
            len(captured_patches) >= 1,
            "patch_async should have been called to reset the queue state",
        )
        last_patch_id, last_patch_updates = captured_patches[-1]
        self.assertEqual(last_patch_id, published_item_id)
        self.assertEqual(
            last_patch_updates[QUEUE_STATE],
            PublishState.PENDING,
            "queue_state must be reset to 'pending' so the background worker can retry",
        )

    async def test_cancellation_resets_to_pending_and_cleans_incomplete_queue_items_when_rows_exist(self):
        exchange = self._make_exchange()

        published_item_id = ObjectId()
        published_item = {
            "_id": published_item_id,
            "item_id": "test-item-1",
            "state": "published",
            "queue_state": "in_progress",
            "type": "text",
            "operation": "publish",
        }

        captured_patches = []

        async def fake_patch(item_id, updates):
            captured_patches.append((item_id, updates.copy()))

        published_service = MagicMock()
        published_service.patch_async = AsyncMock(side_effect=fake_patch)

        request = MagicMock()
        request.item = MagicMock(**published_item)
        request.item.get = MagicMock(return_value=None)
        request.item_id = "test-item-1"
        request.operation = "publish"

        with patch(
            "superdesk.publish_async.exchanges.content_exchange.PublishCache.init",
            new_callable=AsyncMock,
        ):
            with patch(
                "superdesk.publish_async.exchanges.content_exchange.get_resource_service",
                return_value=published_service,
            ):
                with patch.object(
                    exchange,
                    "get_published_item_from_request",
                    new_callable=AsyncMock,
                    return_value=published_item,
                ):
                    with patch.object(
                        exchange,
                        "update_published_item",
                        new_callable=AsyncMock,
                    ):
                        with patch.object(
                            exchange,
                            "_has_publish_queue_items",
                            new_callable=AsyncMock,
                            return_value=True,
                        ):
                            with patch.object(
                                exchange,
                                "_clear_incomplete_publish_queue_items",
                                new_callable=AsyncMock,
                            ) as clear_queue_items:
                                with patch.object(
                                    exchange,
                                    "_publish_item",
                                    new_callable=AsyncMock,
                                    side_effect=asyncio.CancelledError("request cancelled"),
                                ):
                                    with self.assertRaises(asyncio.CancelledError):
                                        await exchange.send(request)

        clear_queue_items.assert_awaited_once_with(request)

        self.assertTrue(len(captured_patches) >= 1)
        last_patch_id, last_patch_updates = captured_patches[-1]
        self.assertEqual(last_patch_id, published_item_id)
        self.assertEqual(last_patch_updates[QUEUE_STATE], PublishState.PENDING)

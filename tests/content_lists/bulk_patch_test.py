# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from unittest import mock

from bson import ObjectId

from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError
from superdesk.tests import TestCase
from superdesk.default_settings import DATE_FORMAT

from apps.content_lists.service import ContentListsService, ContentListItemsService, ITEMS_UPDATED_EVENT


class ContentListBulkPatchTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.lists_service = ContentListsService()
        self.items_service = ContentListItemsService()
        self.content_list = (await self.lists_service.create([{"name": "Test list", "type": "manual"}]))[0]
        self.list_id = self.content_list.id
        archive = self.async_app.mongo.get_collection_async("archive")
        await archive.insert_many(
            [{"_id": f"article-{i}", "guid": f"article-{i}", "type": "text"} for i in range(1, 5)]
        )

    async def _bulk_patch(self, data):
        return await self.items_service.bulk_patch(self.list_id, data)

    async def _stored_updated_at(self):
        content_list = await self.lists_service.find_by_id(self.list_id)
        assert content_list is not None
        return content_list.content_list_items_updated_at

    async def _positions(self):
        items = await self.items_service.get_all_list({"list_id": self.list_id})
        return {item.content: item.position for item in items}

    async def test_empty_body_400(self):
        with self.assertRaises(SuperdeskApiError) as ctx:
            await self._bulk_patch({})
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_missing_items_400(self):
        with self.assertRaises(SuperdeskApiError) as ctx:
            await self._bulk_patch({"updatedAt": "2026-01-01T00:00:00+0000"})
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_missing_updated_at_400(self):
        with self.assertRaises(SuperdeskApiError) as ctx:
            await self._bulk_patch({"items": []})
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_unknown_list_404(self):
        with self.assertRaises(SuperdeskApiError) as ctx:
            await self.items_service.bulk_patch(ObjectId(), {"items": [], "updatedAt": "x"})
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_stale_updated_at_409(self):
        await self.lists_service.mongo_async.update_one(
            {"_id": self.list_id},
            {"$set": {"content_list_items_updated_at": utcnow()}},
        )
        with self.assertRaises(SuperdeskApiError) as ctx:
            await self._bulk_patch({"items": [], "updatedAt": "2000-01-01T00:00:00+0000"})
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_none_stored_timestamp_accepts_any_updated_at(self):
        # A list whose items were never patched has no stored timestamp, so
        # the optimistic concurrency check passes for any updatedAt value.
        self.assertIsNone(await self._stored_updated_at())
        result = await self._bulk_patch({"items": [], "updatedAt": "whatever"})
        self.assertIsNotNone(result.content_list_items_updated_at)

    async def test_matching_updated_at_passes(self):
        await self._bulk_patch({"items": [], "updatedAt": "irrelevant"})
        stored = await self._stored_updated_at()
        result = await self._bulk_patch({"items": [], "updatedAt": stored.strftime(DATE_FORMAT)})
        self.assertIsNotNone(result.content_list_items_updated_at)

    async def test_add_move_delete_actions_and_renumber(self):
        await self._bulk_patch(
            {
                "items": [
                    {"action": "add", "contentId": "article-1", "position": 0},
                    {"action": "add", "contentId": "article-2", "position": 1},
                    {"action": "add", "contentId": "article-3", "position": 2},
                ],
                "updatedAt": "initial",
            }
        )
        self.assertEqual(await self._positions(), {"article-1": 0, "article-2": 1, "article-3": 2})

        stored = await self._stored_updated_at()
        await self._bulk_patch(
            {
                "items": [
                    {"action": "move", "contentId": "article-3", "position": 0},
                    {"action": "delete", "contentId": "article-2"},
                ],
                "updatedAt": stored.strftime(DATE_FORMAT),
            }
        )
        self.assertEqual(await self._positions(), {"article-3": 0, "article-1": 1})

    async def test_move_preserves_sticky_when_omitted(self):
        await self._bulk_patch(
            {
                "items": [{"action": "add", "contentId": "article-1", "position": 0, "sticky": True}],
                "updatedAt": "initial",
            }
        )
        stored = await self._stored_updated_at()
        await self._bulk_patch(
            {
                "items": [{"action": "move", "contentId": "article-1", "position": 2}],
                "updatedAt": stored.strftime(DATE_FORMAT),
            }
        )
        item = await self.items_service.find_one(req=None, list_id=self.list_id, content="article-1")
        self.assertTrue(item.sticky)
        self.assertEqual(item.position, 2)

    async def test_move_unknown_item_is_noop(self):
        result = await self._bulk_patch(
            {
                "items": [{"action": "move", "contentId": "article-1", "position": 0}],
                "updatedAt": "initial",
            }
        )
        self.assertEqual(await self._positions(), {})
        self.assertIsNotNone(result.content_list_items_updated_at)

    async def test_delete_unknown_item_is_noop(self):
        result = await self._bulk_patch(
            {
                "items": [{"action": "delete", "contentId": "article-1"}],
                "updatedAt": "initial",
            }
        )
        self.assertEqual(await self._positions(), {})
        self.assertIsNotNone(result.content_list_items_updated_at)

    async def test_timestamp_written_despite_on_update_strip(self):
        # ``on_update`` strips ``content_list_items_updated_at`` from regular
        # updates; bulk_patch must still manage to write it via mongo directly.
        result = await self._bulk_patch({"items": [], "updatedAt": "initial"})
        self.assertIsNotNone(result.content_list_items_updated_at)
        self.assertIsNotNone(await self._stored_updated_at())

    async def test_push_notification_emitted(self):
        with mock.patch("apps.content_lists.service.push_notification") as push_mock:
            await self._bulk_patch({"items": [], "updatedAt": "initial"})
        push_mock.assert_called_once_with(ITEMS_UPDATED_EVENT, list_id=str(self.list_id), extension="content-lists")

    async def test_enqueue_webhook_deliveries_called(self):
        with mock.patch(
            "apps.content_lists.service.enqueue_webhook_deliveries", new_callable=mock.AsyncMock
        ) as enqueue_mock:
            await self._bulk_patch({"items": [], "updatedAt": "initial"})
        enqueue_mock.assert_awaited_once_with(ITEMS_UPDATED_EVENT, self.list_id)

    async def test_enqueue_not_called_on_conflict(self):
        await self.lists_service.mongo_async.update_one(
            {"_id": self.list_id},
            {"$set": {"content_list_items_updated_at": utcnow()}},
        )
        with mock.patch(
            "apps.content_lists.service.enqueue_webhook_deliveries", new_callable=mock.AsyncMock
        ) as enqueue_mock:
            with self.assertRaises(SuperdeskApiError):
                await self._bulk_patch({"items": [], "updatedAt": "2000-01-01T00:00:00+0000"})
        enqueue_mock.assert_not_awaited()

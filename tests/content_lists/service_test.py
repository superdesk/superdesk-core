# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime, timezone
from unittest import mock

from bson import ObjectId

from superdesk.tests import TestCase

from apps.content_lists.service import (
    ContentListsService,
    ContentListItemsService,
    ITEMS_UPDATED_EVENT,
    LIST_CREATED_EVENT,
    LIST_UPDATED_EVENT,
    LIST_DELETED_EVENT,
)


def _patch_hooks():
    return (
        mock.patch("apps.content_lists.service.push_notification"),
        mock.patch("apps.content_lists.service.enqueue_webhook_deliveries", new_callable=mock.AsyncMock),
    )


class ContentListsServiceHooksTestCase(TestCase):
    """Push notifications and webhook enqueueing on list lifecycle hooks."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = ContentListsService()
        self.items_service = ContentListItemsService()

    async def _create_list(self):
        return (await self.service.create([{"name": "Test list", "type": "manual"}]))[0]

    async def test_on_created_pushes_notification_and_enqueues_webhook(self):
        push_patch, enqueue_patch = _patch_hooks()
        with push_patch as push_mock, enqueue_patch as enqueue_mock:
            content_list = await self._create_list()

        push_mock.assert_called_once_with(LIST_CREATED_EVENT, _id=str(content_list.id), extension="content-lists")
        enqueue_mock.assert_awaited_once_with(LIST_CREATED_EVENT, content_list.id)

    async def test_on_updated_pushes_and_enqueues(self):
        content_list = await self._create_list()
        push_patch, enqueue_patch = _patch_hooks()
        with push_patch as push_mock, enqueue_patch as enqueue_mock:
            await self.service.update(content_list.id, {"description": "updated"})

        push_mock.assert_called_once_with(LIST_UPDATED_EVENT, _id=str(content_list.id), extension="content-lists")
        enqueue_mock.assert_awaited_once_with(LIST_UPDATED_EVENT, content_list.id)

    async def test_on_deleted_cascades_items_and_enqueues(self):
        content_list = await self._create_list()
        items_collection = self.async_app.mongo.get_collection_async("content_list_items")
        await items_collection.insert_many(
            [
                {"_id": ObjectId(), "list_id": content_list.id, "content": "a", "position": 0},
                {"_id": ObjectId(), "list_id": content_list.id, "content": "b", "position": 1},
            ]
        )

        push_patch, enqueue_patch = _patch_hooks()
        with push_patch as push_mock, enqueue_patch as enqueue_mock:
            await self.service.delete(content_list)

        self.assertEqual(await items_collection.count_documents({"list_id": content_list.id}), 0)
        push_mock.assert_called_once_with(LIST_DELETED_EVENT, _id=str(content_list.id), extension="content-lists")
        enqueue_mock.assert_awaited_once_with(LIST_DELETED_EVENT, content_list.id)

    async def test_on_update_strips_server_managed_timestamp(self):
        content_list = await self._create_list()
        await self.service.update(
            content_list.id,
            {
                "description": "updated",
                "content_list_items_updated_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            },
        )
        updated = await self.service.find_by_id(content_list.id)
        self.assertEqual(updated.description, "updated")
        self.assertIsNone(updated.content_list_items_updated_at)

    async def test_bulk_patch_does_not_trigger_list_updated_webhook(self):
        # bulk_patch writes the list timestamp via mongo directly, bypassing
        # the update pipeline: a single batch must produce exactly one
        # items-updated delivery and no list-updated delivery.
        content_list = await self._create_list()
        push_patch, enqueue_patch = _patch_hooks()
        with push_patch, enqueue_patch as enqueue_mock:
            await self.items_service.bulk_patch(content_list.id, {"items": [], "updatedAt": "initial"})

        enqueue_mock.assert_awaited_once_with(ITEMS_UPDATED_EVENT, content_list.id)

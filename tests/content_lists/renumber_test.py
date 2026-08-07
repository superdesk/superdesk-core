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

from superdesk.tests import TestCase

from apps.content_lists.service import ContentListItemsService


class ContentListItemsRenumberTestCase(TestCase):
    """Unit tests for the position renumbering algorithm against MongoDB."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.list_id = ObjectId()
        self.service = ContentListItemsService()
        self.collection = self.async_app.mongo.get_collection_async("content_list_items")

    async def _seed(self, items):
        """Insert raw item docs directly, bypassing model validation.

        ObjectIds are generated in order, so the ``_id`` tiebreak in the
        renumbering algorithm follows the seeding order.
        """
        docs = []
        for item in items:
            doc = {"_id": ObjectId(), "list_id": self.list_id, "sticky": False, "enabled": True}
            doc.update(item)
            docs.append(doc)
        await self.collection.insert_many(docs)
        return docs

    async def _positions(self):
        docs = await self.collection.find({"list_id": self.list_id}).to_list(None)
        return {doc["content"]: doc.get("position") for doc in docs}

    async def test_empty_list_is_noop(self):
        collection = self.service.mongo_async
        with mock.patch.object(type(collection), "bulk_write", new_callable=mock.AsyncMock) as bulk_write_mock:
            await self.service._renumber(self.list_id, [])
        bulk_write_mock.assert_not_awaited()

    async def test_sticky_keeps_declared_position(self):
        await self._seed(
            [
                {"content": "a", "position": 0},
                {"content": "b", "position": 1},
                {"content": "sticky", "position": 2, "sticky": True},
            ]
        )
        await self.service._renumber(self.list_id, [])
        self.assertEqual(await self._positions(), {"a": 0, "b": 1, "sticky": 2})

    async def test_multi_sticky_collision_spills_by_id_order(self):
        await self._seed(
            [
                {"content": "sticky1", "position": 2, "sticky": True},
                {"content": "sticky2", "position": 2, "sticky": True},
            ]
        )
        await self.service._renumber(self.list_id, [])
        # Neither is touched, so the lower _id (seeded first) keeps the slot.
        self.assertEqual(await self._positions(), {"sticky1": 2, "sticky2": 3})

    async def test_multi_sticky_collision_most_recently_touched_wins(self):
        await self._seed(
            [
                {"content": "sticky1", "position": 2, "sticky": True},
                {"content": "sticky2", "position": 2, "sticky": True},
            ]
        )
        await self.service._renumber(self.list_id, ["sticky2"])
        self.assertEqual(await self._positions(), {"sticky2": 2, "sticky1": 3})

    async def test_touched_nonsticky_anchors_but_loses_to_sticky(self):
        await self._seed(
            [
                {"content": "sticky", "position": 1, "sticky": True},
                {"content": "moved", "position": 1},
            ]
        )
        await self.service._renumber(self.list_id, ["moved"])
        self.assertEqual(await self._positions(), {"sticky": 1, "moved": 2})

    async def test_none_and_negative_positions_clamp_to_zero(self):
        await self._seed(
            [
                {"content": "none-pos", "position": None, "sticky": True},
                {"content": "negative", "position": -5, "sticky": True},
            ]
        )
        await self.service._renumber(self.list_id, [])
        # Both clamp to slot 0; the second sticky spills to the next free slot.
        self.assertEqual(await self._positions(), {"none-pos": 0, "negative": 1})

    async def test_untouched_nonsticky_pack_into_lowest_free_slots_in_prior_order(self):
        await self._seed(
            [
                {"content": "high", "position": 5},
                {"content": "low", "position": 3},
                {"content": "unpositioned", "position": None},
                {"content": "sticky", "position": 1, "sticky": True},
            ]
        )
        await self.service._renumber(self.list_id, [])
        # Sticky anchors at 1; the rest pack into free slots 0, 2, 3 ordered by
        # previous position, with None-position items last.
        self.assertEqual(await self._positions(), {"sticky": 1, "low": 0, "high": 2, "unpositioned": 3})

    async def test_only_changed_positions_are_written(self):
        await self._seed(
            [
                {"content": "a", "position": 0},
                {"content": "b", "position": 1},
            ]
        )
        collection = self.service.mongo_async
        with mock.patch.object(type(collection), "bulk_write", new_callable=mock.AsyncMock) as bulk_write_mock:
            await self.service._renumber(self.list_id, [])
        bulk_write_mock.assert_not_awaited()

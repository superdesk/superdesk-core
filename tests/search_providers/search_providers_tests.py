# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from unittest.mock import MagicMock

import superdesk
from superdesk import SearchProvider
from superdesk.tests import TestCase
from superdesk.eve_async import AsyncListCursor
from superdesk.utils import ListCursor
from apps.search_providers.service import SearchProviderService
from apps.search_providers import register_search_provider
from superdesk.errors import AlreadyExistsError


class MockAsyncCursorProvider(SearchProvider):
    async def find_async(self, query, params=None):
        return AsyncListCursor([{"guid": "async_item_1", "headline": "Test Async"}])


class MockListProvider(SearchProvider):
    async def find_async(self, query, params=None):
        return [{"guid": "list_item_1", "headline": "Test List"}]


class MockListCursorProvider(SearchProvider):
    async def find_async(self, query, params=None):
        return ListCursor([{"guid": "cursor_item_1", "headline": "Test Cursor"}])


class SearchProviderTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = SearchProviderService("search_providers", backend=superdesk.get_backend())
        try:
            register_search_provider("provider1", "provider1")
            register_search_provider("provider2", "provider2")
        except AlreadyExistsError:
            pass

    async def test_set_is_default_on_create(self):
        provider1 = {"search_provider": "provider1", "source": "provider1", "is_default": True}
        provider2 = {"search_provider": "provider2", "source": "provider2", "is_default": True}
        provider1_id = (await self.service.post_async([provider1]))[0]
        provider2_id = (await self.service.post_async([provider2]))[0]
        provider1 = await self.service.find_one_async(req=None, _id=provider1_id)
        provider2 = await self.service.find_one_async(req=None, _id=provider2_id)
        self.assertEqual(provider1["is_default"], False)
        self.assertEqual(provider2["is_default"], True)

    async def test_set_is_default_on_update(self):
        provider1 = {"search_provider": "provider1", "source": "provider1", "is_default": False}
        provider2 = {"search_provider": "provider2", "source": "provider2", "is_default": True}
        provider1_id = (await self.service.post_async([provider1]))[0]
        provider2_id = (await self.service.post_async([provider2]))[0]
        await self.service.patch_async(provider1_id, {"is_default": True})
        provider1 = await self.service.find_one_async(req=None, _id=provider1_id)
        provider2 = await self.service.find_one_async(req=None, _id=provider2_id)
        self.assertEqual(provider1["is_default"], True)
        self.assertEqual(provider2["is_default"], False)

    async def test_proxy_get_async_with_async_list_cursor(self):
        try:
            register_search_provider("async_provider", provider_class=MockAsyncCursorProvider)
        except AlreadyExistsError:
            pass
        provider = {"search_provider": "async_provider", "source": "async_provider"}
        provider_id = (await self.service.post_async([provider]))[0]

        proxy_service = superdesk.get_resource_service("search_providers_proxy")
        req = MagicMock()
        req.args = {"repo": str(provider_id)}

        items = await proxy_service.get_async(req, lookup={})
        self.assertIsInstance(items, AsyncListCursor)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["guid"], "async_item_1")
        self.assertEqual(item["_id"], "async_item_1")
        self.assertEqual(item["_type"], "externalsource")
        self.assertEqual(item["ingest_provider"], str(provider_id))

        # Test both sync iteration and async iteration
        sync_items = [doc for doc in items]
        self.assertEqual(len(sync_items), 1)
        async_items = [doc async for doc in items]
        self.assertEqual(len(async_items), 1)

    async def test_proxy_get_async_with_list(self):
        try:
            register_search_provider("list_provider", provider_class=MockListProvider)
        except AlreadyExistsError:
            pass
        provider = {"search_provider": "list_provider", "source": "list_provider"}
        provider_id = (await self.service.post_async([provider]))[0]

        proxy_service = superdesk.get_resource_service("search_providers_proxy")
        req = MagicMock()
        req.args = {"repo": str(provider_id)}

        items = await proxy_service.get_async(req, lookup={})
        self.assertIsInstance(items, AsyncListCursor)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["guid"], "list_item_1")
        self.assertEqual(item["_id"], "list_item_1")
        self.assertEqual(item["_type"], "externalsource")

    async def test_proxy_get_async_with_list_cursor(self):
        try:
            register_search_provider("list_cursor_provider", provider_class=MockListCursorProvider)
        except AlreadyExistsError:
            pass
        provider = {"search_provider": "list_cursor_provider", "source": "list_cursor_provider"}
        provider_id = (await self.service.post_async([provider]))[0]

        proxy_service = superdesk.get_resource_service("search_providers_proxy")
        req = MagicMock()
        req.args = {"repo": str(provider_id)}

        items = await proxy_service.get_async(req, lookup={})
        self.assertIsInstance(items, AsyncListCursor)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["guid"], "cursor_item_1")
        self.assertEqual(item["_id"], "cursor_item_1")
        self.assertEqual(item["_type"], "externalsource")

    async def test_async_list_cursor_methods(self):
        docs = [{"_id": 1, "name": "one"}, {"_id": 2, "name": "two"}, {"_id": 3, "name": "three"}]
        cursor = AsyncListCursor(docs)

        # len, indexing, first
        self.assertEqual(len(cursor), 3)
        self.assertEqual(cursor[0], {"_id": 1, "name": "one"})
        self.assertEqual(cursor.first(), {"_id": 1, "name": "one"})

        # sync iteration
        sync_items = [d for d in cursor]
        self.assertEqual(sync_items, docs)

        # async iteration
        async_items = [d async for d in cursor]
        self.assertEqual(async_items, docs)

        # test sync iteration with skip and limit
        cursor_window = AsyncListCursor(docs).skip(1).limit(2)
        # sync iteration respects skip and limit without consuming _index
        self.assertEqual(cursor_window._index, 1)
        self.assertEqual([d for d in cursor_window], docs[1:2])
        self.assertEqual(cursor_window._index, 1)

        # async iteration also respects the same window
        self.assertEqual([d async for d in cursor_window], docs[1:2])

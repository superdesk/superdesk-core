from unittest.mock import AsyncMock, patch
from superdesk.tests import AsyncTestCase

from superdesk.core.module import Module
from superdesk.core.resources import ResourceModel, ResourceConfig, AsyncCacheableService


class TestAsyncCacheableService(AsyncCacheableService[ResourceModel]):
    resource_name = "tests_cacheable"


model_config = ResourceConfig(name="tests_cacheable", data_class=ResourceModel, service=TestAsyncCacheableService)
module = Module(name="tests.cacheable", resources=[model_config])


class AsyncCacheableServiceTestCase(AsyncTestCase):
    app_config = {"MONGO_DBNAME": "sptests", "MODULES": ["tests.core.cacheable_service_test"]}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = TestAsyncCacheableService()

        self.patcher1 = patch("superdesk.core.resources.service.cache")
        self.patcher2 = patch.object(TestAsyncCacheableService, "get_cache")
        self.patcher3 = patch.object(TestAsyncCacheableService, "set_cache")
        self.patcher4 = patch.object(TestAsyncCacheableService, "search")

        self.mock_cache = self.patcher1.start()
        self.mock_get_cache = self.patcher2.start()
        self.mock_set_cache = self.patcher3.start()
        self.mock_search = self.patcher4.start()

        # make cache decorator to directly return the function
        self.mock_cache.side_effect = lambda *args, **kwargs: lambda fn: fn

    async def asyncTearDown(self):
        self.addCleanup(self.patcher1.stop)
        self.addCleanup(self.patcher2.stop)
        self.addCleanup(self.patcher3.stop)
        self.addCleanup(self.patcher4.stop)

        await super().asyncTearDown()

    async def test_get_cached_from_db(self):
        mock_cursor = AsyncMock()
        mock_cursor.to_list_raw = AsyncMock(return_value=[{"_id": "1", "data": "test"}])
        self.mock_search.return_value = mock_cursor
        self.mock_get_cache.return_value = None

        result = await self.service.get_cached()

        assert result == [{"_id": "1", "data": "test"}]
        self.mock_get_cache.is_called_once()
        self.mock_set_cache.assert_called_once_with([{"_id": "1", "data": "test"}])
        self.mock_search.assert_called_once()

    async def test_get_cached_by_id_found_in_cache(self):
        self.mock_get_cache.return_value = [{"_id": "1", "data": "test"}]

        result = await self.service.get_cached_by_id("1")

        assert result == {"_id": "1", "data": "test"}
        self.mock_get_cache.assert_called_once()
        self.mock_set_cache.assert_not_called()
        self.mock_search.assert_not_called()

    @patch.object(TestAsyncCacheableService, "find_by_id", return_value={"_id": "1", "data": "from_db"})
    async def test_get_cached_by_id_NOT_found_in_cache(self, mock_find_by_id):
        self.mock_get_cache.return_value = [{"_id": "2", "data": "test"}]

        result = await self.service.get_cached_by_id("1")
        assert result == {"_id": "1", "data": "from_db"}

        self.mock_get_cache.assert_called_once()
        self.mock_set_cache.assert_not_called()
        mock_find_by_id.assert_called_once_with("1")

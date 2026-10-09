import asyncio
import unittest
from unittest.mock import MagicMock, patch

from redis.exceptions import TimeoutError as RedisTimeoutError, ConnectionError as RedisConnectionError

from superdesk.celery_app.task_result import AsyncTaskResult


real_sleep = asyncio.sleep


def make_result(ready, get_task_meta) -> AsyncTaskResult:
    # Bypass AsyncResult.__init__, which needs a configured celery app
    result = AsyncTaskResult.__new__(AsyncTaskResult)
    result.id = "task-id"
    result.ready = ready  # type: ignore[method-assign]
    result.backend = MagicMock()
    result.backend.get_task_meta = get_task_meta
    return result


class AsyncTaskResultTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        sleep_patch = patch("superdesk.celery_app.task_result.asyncio.sleep", side_effect=self._fast_sleep)
        self.sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    @staticmethod
    async def _fast_sleep(_delay):
        await real_sleep(0)

    async def test_returns_result(self):
        result = make_result(MagicMock(return_value=True), MagicMock(return_value={"result": [None, {"a": 1}]}))
        self.assertEqual(await result.get_result_async(), {"a": 1})

    async def test_retries_ready_on_redis_timeout(self):
        ready = MagicMock(side_effect=[RedisTimeoutError("t"), RedisConnectionError("c"), True])
        meta = MagicMock(return_value={"result": [None, "ok"]})
        result = make_result(ready, meta)
        self.assertEqual(await result.get_result_async(), "ok")
        self.assertEqual(ready.call_count, 3)

    async def test_retries_get_task_meta_on_redis_timeout(self):
        meta = MagicMock(side_effect=[RedisTimeoutError("t"), {"result": [None, "ok"]}])
        result = make_result(MagicMock(return_value=True), meta)
        self.assertEqual(await result.get_result_async(), "ok")
        self.assertEqual(meta.call_count, 2)

    async def test_raises_after_max_retries(self):
        ready = MagicMock(side_effect=RedisTimeoutError("t"))
        result = make_result(ready, MagicMock())
        with self.assertRaises(RedisTimeoutError):
            await result.get_result_async(max_retries=2)
        self.assertEqual(ready.call_count, 3)

    async def test_non_redis_errors_not_retried(self):
        ready = MagicMock(side_effect=ValueError("boom"))
        result = make_result(ready, MagicMock())
        with self.assertRaises(ValueError):
            await result.get_result_async()
        self.assertEqual(ready.call_count, 1)

    async def test_raises_task_exception(self):
        result = make_result(MagicMock(return_value=True), MagicMock(return_value={"result": ValueError("failed")}))
        with self.assertRaises(ValueError):
            await result.get_result_async()

    async def test_timeout_when_never_ready(self):
        result = make_result(MagicMock(return_value=False), MagicMock())
        with self.assertRaises(asyncio.TimeoutError):
            await result.get_result_async(max_timeout=0)

    async def test_deadline_stops_retries(self):
        ready = MagicMock(side_effect=RedisTimeoutError("t"))
        result = make_result(ready, MagicMock())
        with self.assertRaises(RedisTimeoutError):
            await result.get_result_async(max_timeout=0, max_retries=100)
        self.assertEqual(ready.call_count, 1)

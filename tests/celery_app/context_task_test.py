import asyncio
from unittest.mock import patch

from superdesk.errors import SuperdeskError
from superdesk.celery_app import HybridAppContextTask
from superdesk.tests import AsyncFlaskTestCase

# NOTE: all tasks below are in eager mode because of global
# tests settings. See `update_config` function in tests.__init__.py


class TestHybridAppContextTask(AsyncFlaskTestCase):
    async def test_sync_task(self):
        @self.app.celery.task()
        def sync_task():
            return "sync result"

        result = await sync_task.apply_async()
        self.assertEqual(result, "sync result")

    async def test_async_task(self):
        @self.app.celery.task()
        async def async_task():
            await asyncio.sleep(0.1)
            return "async result"

        result = await async_task.apply_async()
        self.assertEqual(result, "async result")

    async def test_sync_task_exception(self):
        @self.app.celery.task()
        def sync_task_exception():
            raise SuperdeskError("Test exception")

        with patch("superdesk.celery_app.context_task.logger") as mock_logger:
            await sync_task_exception.apply_async()
            expected_exc = SuperdeskError("Test exception")
            expected_msg = f"Error handling task: {str(expected_exc)}"
            mock_logger.exception.assert_called_once_with(expected_msg)

    async def test_async_task_exception(self):
        @self.app.celery.task()
        async def async_task_exception():
            raise SuperdeskError("Async exception")

        with patch("superdesk.celery_app.context_task.logger") as mock_logger:
            await async_task_exception.apply_async()

            expected_exc = SuperdeskError("Async exception")
            expected_msg = f"Error handling task: {str(expected_exc)}"
            mock_logger.exception.assert_called_once_with(expected_msg)

    async def test_configured_always_eager_follows_config(self):
        @self.app.celery.task()
        def some_task():
            return "ok"

        self.assertTrue(some_task._is_configured_always_eager())


class TestEagerDispatchDecision(AsyncFlaskTestCase):
    app_config = {"CELERY_TASK_ALWAYS_EAGER": False}

    async def test_unbound_dispatch_is_config_driven(self):
        @self.app.celery.task()
        def some_task():
            return "ok"

        self.assertFalse(some_task._is_configured_always_eager())
        self.assertTrue(some_task._is_always_eager())

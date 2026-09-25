import asyncio
from unittest.mock import patch

from celery.app.trace import build_tracer
from kombu.utils.uuid import uuid

from superdesk.errors import SuperdeskError
from superdesk.celery_app import HybridAppContextTask
from superdesk.tests import AsyncFlaskTestCase
from superdesk.tests import worker_test

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

        self.assertEqual(
            some_task._is_configured_always_eager(),
            self.app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
        )


class TestEagerDispatchDecision(AsyncFlaskTestCase):
    app_config = {"CELERY_TASK_ALWAYS_EAGER": False}

    async def test_unbound_task_eager_decision(self):
        @self.app.celery.task()
        def some_task():
            return "ok"

        self.assertFalse(some_task._is_configured_always_eager())
        self.assertTrue(some_task._is_always_eager())


class TestStoreAsyncResultInWorker(AsyncFlaskTestCase):
    """Runs tasks the way the default (non-async) worker does, through Celery's non-eager tracer.

    The test harness forces eager mode unless ``CELERY_USE_ASYNC_WORKER`` is on, so this is the only
    coverage of how a result reaches ``AsyncTaskResult`` from a default ``celery worker`` process.
    """

    app_config = {"CELERY_TASK_ALWAYS_EAGER": False}

    async def _run_in_worker(self, task, *args) -> str:
        task_id = uuid()
        tracer = build_tracer(task.name, task, eager=False, app=self.app.celery)

        def run():
            # A worker process has no running event loop, so ``run_async`` drives its own
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # ``ignore_result`` is what every task message carries while ``CELERY_TASK_IGNORE_RESULT`` is on
                tracer(task_id, args, {}, {"id": task_id, "ignore_result": True})
            finally:
                asyncio.set_event_loop(None)
                loop.close()

        await asyncio.to_thread(run)

        return task_id

    async def test_result_is_stored(self):
        # Resolve the ``shared_task`` proxy here: in another thread it would bind to Celery's default app
        task = worker_test.value_task_test._get_current_object()
        task_id = await self._run_in_worker(task, 21)
        result = await task.AsyncResult(task_id).get_result_async(max_timeout=5)
        self.assertEqual(result, 42)

    async def test_app_error_is_stored(self):
        @self.app.celery.task(store_async_result=True)
        async def failing_task():
            raise SuperdeskError("Rendering failed")

        with patch("superdesk.celery_app.context_task.logger"):
            task_id = await self._run_in_worker(failing_task)

        with self.assertRaises(Exception) as context:
            await failing_task.AsyncResult(task_id).get_result_async(max_timeout=5)
        self.assertNotIsInstance(context.exception, asyncio.TimeoutError)
        self.assertIn("Rendering failed", str(context.exception))

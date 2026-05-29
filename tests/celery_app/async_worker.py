import asyncio
from subprocess import Popen
from unittest.mock import patch, MagicMock
import time
import threading

from superdesk import get_resource_service
from superdesk.celery_app.async_worker import CeleryAsyncWorkerThread

from superdesk.tests import TestCase
from superdesk.tests.worker import run_celery_in_background, async_task_test, sync_task_test


class CeleryAsyncWorkerTestCase(TestCase):
    app_config = {"CELERY_USE_ASYNC_WORKER": True}
    _celery_process: Popen

    @classmethod
    async def asyncSetUpClass(cls):
        await super().asyncSetUpClass()
        cls._celery_process = run_celery_in_background()

    @classmethod
    async def asyncTearDownClass(cls):
        await super().asyncTearDownClass()
        cls._celery_process.terminate()
        cls._celery_process.wait()

    async def test_celery_worker_is_running(self):
        assert self.app.celery.control.inspect().ping() is not None

    async def _wait_for_celery_task(self):
        """Wait for the celery task to be processed

        Using the test tasks, the "system_messages" resource should have 1 new message.
        """

        service = get_resource_service("system_messages")
        runs = 0
        while await service.count_async() == 0 and runs < 10:
            await asyncio.sleep(0.5)
            runs += 1

    async def test_sync_worker(self):
        await async_task_test.delay(
            {
                "is_active": True,
                "type": "success",
                "message_title": "Test Async Celery 1",
                "message": "Testing async celery worker and task",
            }
        )

        service = get_resource_service("system_messages")
        await self._wait_for_celery_task()
        self.assertEqual(await service.count_async(), 1)
        message = await service.find_one_async(req=None, type="success")
        self.assertDictContains(
            message,
            {
                "is_active": True,
                "type": "success",
                "message_title": "Test Async Celery 1",
                "message": "Testing async celery worker and task",
            },
        )

    async def test_async_worker(self):
        await sync_task_test.delay(
            {
                "is_active": True,
                "type": "warning",
                "message_title": "Test Async Celery 2",
                "message": "Testing async celery worker and task",
            }
        )
        service = get_resource_service("system_messages")
        await self._wait_for_celery_task()
        self.assertEqual(await service.count_async(), 1)
        message = await service.find_one_async(req=None, type="warning")
        self.assertDictContains(
            message,
            {
                "is_active": True,
                "type": "warning",
                "message_title": "Test Async Celery 2",
                "message": "Testing async celery worker and task",
            },
        )

    async def test_sync_worker_eager(self):
        with patch.dict(self.app_config, {"CELERY_ALWAYS_EAGER": True}):
            await async_task_test.delay(
                {
                    "is_active": True,
                    "type": "success",
                    "message_title": "Test Async Celery 1",
                    "message": "Testing async celery worker and task",
                }
            )

        service = get_resource_service("system_messages")
        self.assertEqual(await service.count_async(), 1)
        message = await service.find_one_async(req=None, type="success")
        self.assertDictContains(
            message,
            {
                "is_active": True,
                "type": "success",
                "message_title": "Test Async Celery 1",
                "message": "Testing async celery worker and task",
            },
        )

    async def test_async_worker_eager(self):
        with patch.dict(self.app_config, {"CELERY_ALWAYS_EAGER": True}):
            await sync_task_test.delay(
                {
                    "is_active": True,
                    "type": "warning",
                    "message_title": "Test Async Celery 2",
                    "message": "Testing async celery worker and task",
                }
            )

        service = get_resource_service("system_messages")
        self.assertEqual(await service.count_async(), 1)
        message = await service.find_one_async(req=None, type="warning")
        self.assertDictContains(
            message,
            {
                "is_active": True,
                "type": "warning",
                "message_title": "Test Async Celery 2",
                "message": "Testing async celery worker and task",
            },
        )


class CeleryAsyncThreadTestCase(TestCase):
    app_config = {
        "CELERY_USE_ASYNC_WORKER": True,
        "CELERY_ASYNC_THREAD_MAX_TASKS": 5,
        "CELERY_ASYNC_THREAD_RESTART_TASKS": 2,
        "CELERY_ASYNC_THREAD_BLOCK_SLEEP": 0.1,
    }

    def test_limit_active_tasks_no_block(self):
        """Test that it doesn't block when under max tasks."""
        worker = CeleryAsyncWorkerThread.get_instance()
        worker._num_tasks = 4  # Less than max_tasks (5)

        start_time = time.time()
        worker.limit_active_tasks()
        end_time = time.time()

        # Should return immediately
        self.assertLess(end_time - start_time, 0.1)

    def test_submit_triggers_limit(self):
        """Test that submit() calls limit_active_tasks()."""
        worker = CeleryAsyncWorkerThread.get_instance()
        with patch.object(worker, "limit_active_tasks") as mock_limit:
            # Mock run_task to avoid actual execution
            with patch.object(worker, "run_task"):
                worker.submit(MagicMock())
                mock_limit.assert_called_once()

    def test_limit_active_tasks_high_load_blocks(self):
        """Test that it blocks when max tasks is reached and resumes on stabilization."""
        worker = CeleryAsyncWorkerThread.get_instance()
        worker._num_tasks = 5  # Reached max_tasks

        def reduce_load():
            # Wait a bit then reduce tasks below restart threshold
            time.sleep(0.3)
            worker._num_tasks = 1

        # Run reduction in a separate thread to unblock the main thread
        timer_thread = threading.Thread(target=reduce_load)

        with self.assertLogs("superdesk.celery_app.async_worker", level="INFO") as logs:
            start_time = time.time()
            timer_thread.start()
            worker.limit_active_tasks()
            end_time = time.time()
            timer_thread.join()

        # Check that it actually blocked for at least the sleep duration
        self.assertGreaterEqual(end_time - start_time, 0.3)

        # Verify log messages
        self.assertTrue(any("Celery high load detected" in msg for msg in logs.output))
        self.assertTrue(any("Load stabilized" in msg for msg in logs.output))

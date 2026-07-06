import asyncio
from subprocess import Popen
from unittest.mock import patch, MagicMock
import time
import threading

from superdesk import get_resource_service
from superdesk.celery_app.async_worker import CeleryAsyncWorkerThread

from superdesk.tests import TestCase, AsyncFlaskTestCase
from superdesk.tests import worker_test


class CeleryAsyncWorkerTaskTestCase(TestCase):
    app_config = {
        "CELERY_USE_ASYNC_WORKER": True,
        "CELERY_TASK_ALWAYS_EAGER": False,
    }
    _celery_process: Popen

    @classmethod
    async def asyncSetUpClass(cls):
        await super().asyncSetUpClass()
        cls._celery_process = worker_test.run_celery_in_background()

    @classmethod
    async def asyncTearDownClass(cls):
        await super().asyncTearDownClass()
        cls._celery_process.terminate()
        cls._celery_process.wait()

    async def _wait_for_celery_task(self, wait_for_count=1):
        """Wait for the celery task to be processed

        Using the test tasks, the "system_messages" resource should have 1 new message.
        """

        service = get_resource_service("system_messages")
        runs = 0
        while await service.count_async() < wait_for_count and runs < 10:
            await asyncio.sleep(0.5)
            runs += 1

    async def test_celery_worker_is_running(self):
        assert self.app.celery.control.inspect().ping() is not None

    async def test_sync_worker(self):
        await worker_test.sync_task_test.delay(
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
        await worker_test.async_task_test.delay(
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

    async def test_task_no_timeout(self):
        service = get_resource_service("system_messages")
        await worker_test.async_task_timeout_test.delay(0, 0)
        await self._wait_for_celery_task()
        messages = await (await service.get_all_async()).to_list()
        assert len(messages) == 1
        self.assertDictContains(messages[0], {"type": "success", "message": "done"})
        assert messages[0]["type"] == "success"

    async def test_task_soft_timeout(self):
        service = get_resource_service("system_messages")
        await worker_test.async_task_timeout_test.delay(1, 0)
        await self._wait_for_celery_task()
        messages = await (await service.get_all_async()).to_list()
        assert len(messages) == 1
        self.assertDictContains(messages[0], {"type": "alert", "message": "asyncio.CancelledError"})

    async def test_task_hard_timeout(self):
        service = get_resource_service("system_messages")
        await worker_test.async_task_timeout_test.delay(0.5, 1)
        await asyncio.sleep(3)
        self.assertEqual(0, await service.count_async())


class CeleryAsyncWorkerEagerTestCase(AsyncFlaskTestCase):
    app_config = {
        "CELERY_USE_ASYNC_WORKER": True,
        "CELERY_TASK_ALWAYS_EAGER": True,
        "INSTALLED_APPS": ["apps.system_message"],
    }

    async def test_sync_worker_eager(self):
        await worker_test.async_task_test.delay(
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
        await worker_test.sync_task_test.delay(
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


class CeleryAsyncThreadTestCase(AsyncFlaskTestCase):
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
        """Test that submit_to_thread() calls limit_active_tasks()."""
        worker = CeleryAsyncWorkerThread.get_instance()
        with patch.object(worker, "limit_active_tasks") as mock_limit:
            # Mock run_task to avoid actual execution
            with patch.object(worker, "run_task"):
                worker.submit_to_thread(MagicMock())
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

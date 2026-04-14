import asyncio
import time
from unittest.mock import patch
from superdesk.core import tasks
from superdesk.tests import AsyncTestCase


class TasksTestCase(AsyncTestCase):
    async def asyncTearDown(self):
        # Clean up any remaining tasks
        await tasks.wait_thread_tasks_to_complete(timeout=1)
        await super().asyncTearDown()

    async def test_run_in_thread(self):
        """Test run_in_thread correctly executes the function and returns a task."""

        def test_func(arg1, kwarg1=None):
            self.assertEqual(arg1, "foo")
            self.assertEqual(kwarg1, "bar")
            return "success"

        task = tasks.run_in_thread(test_func, "foo", kwarg1="bar")

        self.assertIsInstance(task, asyncio.Task)
        self.assertIn(task, tasks._thread_tasks)
        self.assertTrue(task.get_name().startswith("thread_task__"))

        # Wait for the task itself to finish and its callback to run
        await task
        result = task.result()
        self.assertEqual(result, "success")

        # # The task should be removed from _thread_tasks by the callback
        self.assertNotIn(task, tasks._thread_tasks)

    async def test_wait_thread_tasks_to_complete(self):
        """Test wait_thread_tasks_to_complete cancels and waits for tasks."""

        def long_running_func():
            # This will be interrupted if the thread is cancelled,
            time.sleep(5)
            raise Exception("This should not be reached")

        with patch("superdesk.core.tasks.logger") as mock_logger:
            task = tasks.run_in_thread(long_running_func)
            self.assertIn(task, tasks._thread_tasks)

            await tasks.wait_thread_tasks_to_complete(timeout=1)

            mock_logger.warning.assert_called_with(
                "Background task was cancelled", extra={"task_name": task.get_name()}
            )

            self.assertTrue(task.done())
            self.assertTrue(task.cancelled())
            self.assertEqual(len(tasks._thread_tasks), 0)

    async def test_handle_background_task_result_exception(self):
        """Test _handle_background_task_result logs exceptions."""

        def failing_func():
            raise ValueError("test exception")

        with patch("superdesk.core.tasks.logger") as mock_logger:
            task = tasks.run_in_thread(failing_func)

            with self.assertRaises(ValueError):
                await task

            mock_logger.exception.assert_called_with("Background task failed", extra={"task_name": task.get_name()})
            self.assertNotIn(task, tasks._thread_tasks)

    async def test_handle_background_task_result_cancelled(self):
        """Test _handle_background_task_result logs cancellation."""

        def slow_func():
            time.sleep(0.5)

        with patch("superdesk.core.tasks.logger") as mock_logger:
            task = tasks.run_in_thread(slow_func)
            task.cancel()

            with self.assertRaises(asyncio.CancelledError):
                await task

            mock_logger.warning.assert_called_with(
                "Background task was cancelled", extra={"task_name": task.get_name()}
            )
            self.assertNotIn(task, tasks._thread_tasks)

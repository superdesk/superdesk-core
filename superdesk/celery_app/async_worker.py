from typing import Any, Protocol, TYPE_CHECKING
import logging
import asyncio
import threading
from inspect import isawaitable
from time import sleep

from celery.worker.request import Request
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
import werkzeug

from superdesk.errors import SuperdeskError
from .context_task import HybridAppContextWorkerTask

if TYPE_CHECKING:
    from superdesk.factory.app import SuperdeskApp
else:
    SuperdeskApp = Any


logger = logging.getLogger(__name__)


class ThreadData(Protocol):
    worker: "CeleryAsyncWorkerThread"


class CeleryAsyncWorkerTask(HybridAppContextWorkerTask):
    acks_late = True
    store_async_result = False

    def __call__(self, *args, **kwargs):
        if self._is_always_eager():
            return super().__call__(*args, **kwargs)

        # Stop Celery from updating Task state, as we'll handle that manually
        self.task_id = self.request.id
        self.request.acknowledged = True
        CeleryAsyncWorkerThread.get_instance().submit_to_thread(self, *args, **kwargs)
        return self.update_state(state="PROCESSING")

    def on_task_complete(self, task_response) -> None:
        """
        Handles the completion of an asynchronous task by processing the task response.

        This method processes the result of an asynchronous task execution. It marks the
        task as completed successfully, or handles failures and exceptions caused during
        execution. Specific error logging is done for various types of exceptions.

        This method runs in the same process that submitted the task, ensuring that
        task completion is handled in the context where the task was initiated.

        :param task_response: The response object representing the result of the asynchronous task.
        """
        request: Request = self.request
        request.id = self.task_id

        try:
            result = task_response.result()
            logger.info(f"Task {self.name}[{self.task_id}] completed")
            self.backend.mark_as_done(request.id, result, request=request, store_result=self.store_async_result)
        except self.app_errors as error:
            logger.exception(f"CeleryAsyncWorkerThread - App Error: {error}")
            self.backend.mark_as_failure(request.id, error, store_result=self.store_async_result)
        except (SoftTimeLimitExceeded, TimeLimitExceeded) as error:
            logger.exception(f"CeleryAsyncWorkerThread - Task timed out: {error}")
            self.backend.mark_as_failure(request.id, error, store_result=self.store_async_result)
        except asyncio.CancelledError as error:
            logger.exception(f"CeleryAsyncWorkerThread - Task cancelled: {error}")
            self.backend.mark_as_failure(request.id, error, store_result=self.store_async_result)
        except Exception as error:
            logger.exception(f"CeleryAsyncWorkerThread - Task failed: {error}")
            self.backend.mark_as_failure(request.id, error, store_result=self.store_async_result)


class CeleryAsyncWorkerThread(threading.Thread):
    """
    Manages an asynchronous event loop thread for handling Celery tasks.

    This class provides functionality to handle execution of Celery tasks within a
    dedicated asyncio event loop running in a background thread. It is responsible
    for ensuring proper lifecycle management of the event loop, handling task
    submission, limiting the number of active tasks, and performing cleanup of
    background tasks on shutdown.
    """

    #: Thread local storage to store the worker instance (only 1 per process allowed)
    _thread_local: ThreadData = threading.local()

    #: The asyncio event loop used for executing tasks.
    _loop: asyncio.AbstractEventLoop | None = None

    #: Event to signal when the loop is ready to run tasks.
    _loop_ready: threading.Event = threading.Event()

    #: The number of currently active tasks.
    _num_tasks: int = 0

    #: A lock to ensure thread-safe access to the number of active tasks.
    _task_tracker_lock: threading.Lock = threading.Lock()

    #: A local set of currently active tasks.
    _tasks: set[asyncio.Task] = set()

    #: A tuple of exception types that are treated as application errors when running Celery tasks.
    app_errors = (SuperdeskError, werkzeug.exceptions.InternalServerError)

    #: The Superdesk application instance used for pushing the application context.
    wsgi_app: SuperdeskApp

    #: The maximum number of active tasks allowed before task submission is paused.
    _max_tasks: int

    #: The maximum number of active tasks allowed before task submission is resumed.
    _restart_tasks: int

    #: The time, in seconds, to wait before checking the number of active tasks.
    _monitor_sleep: float

    class WorkerNotCreatedException(Exception):
        """Exception used when ``get_instance`` is called with ``raise_if_not_available=True``"""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="CeleryAsyncWorkerThread",
            daemon=True,
            **(kwargs or {}),
        )
        self._loop_ready = threading.Event()
        self._num_tasks = 0
        self._tasks = set()
        self._task_tracker_lock = threading.Lock()
        import superdesk

        assert superdesk.app is not None, "Superdesk app is not initialized"
        self.wsgi_app = superdesk.app

        self._max_tasks = self.wsgi_app.config.get("CELERY_ASYNC_THREAD_MAX_TASKS", 100)
        self._restart_tasks = self.wsgi_app.config.get("CELERY_ASYNC_THREAD_RESTART_TASKS", 20)
        self._monitor_sleep = self.wsgi_app.config.get("CELERY_ASYNC_THREAD_BLOCK_SLEEP", 1)

    @classmethod
    def get_instance(cls, raise_if_not_available: bool = False) -> "CeleryAsyncWorkerThread":
        """
        Provides a thread-safe singleton instance of CeleryAsyncWorkerThread. Ensures that only one
        instance of the worker thread exists and starts the thread if it is not already alive.

        This method is used to manage the lifecycle of the worker thread and provides
        a consistent entry point for acquiring an instance.

        :param raise_if_not_available: If True, an exception will be raised if the worker thread is not available.
        :return: The singleton instance of the CeleryAsyncWorkerThread.
        """

        if not hasattr(cls._thread_local, "worker") or not cls._thread_local.worker.is_alive():
            if raise_if_not_available:
                raise cls.WorkerNotCreatedException()

            cls._thread_local.worker = cls()
            cls._thread_local.worker.start()

        return cls._thread_local.worker

    def run(self):
        """
        Main run function for the thread.

        The `run` method initializes and starts a new asyncio event loop, making it the
        current active event loop. It signals readiness once the loop is set up. This
        method continuously runs the event loop until it is explicitly stopped, ensuring
        all scheduled tasks are executed. Upon termination, it performs necessary cleanup
        activities.
        """

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        try:
            self._loop.run_forever()
        finally:
            self._cleanup()

    def _push_task(self, task: asyncio.Task):
        """
        Adds a new asyncio task to the internal task tracker.

        This method ensures that the task is tracked internally for proper management. Only
        intended for use within the class to handle task bookkeeping in a thread-safe manner.

        :param task: The asyncio task to be added to the tracker.
        """

        with self._task_tracker_lock:
            self._num_tasks += 1
            self._tasks.add(task)

    def _pop_task(self, task: asyncio.Task | None):
        """
        Removes a task from the internal task tracker and updates the total task count.

        If a task is specified, it is removed from the list of tracked tasks. The total
        number of tasks is decremented regardless of whether the task is provided.

        :param task:The task to be removed from the task tracker, or None if no specific task is being removed.
        """

        with self._task_tracker_lock:
            if task is not None:
                self._tasks.remove(task)
            self._num_tasks -= 1

    def _get_num_tasks(self) -> int:
        """
        Retrieves the number of tasks currently being tracked.

        This method acquires a lock to ensure thread-safe access to the internal task
        tracker. It returns the total count of tasks being managed.

        :return: The current number of tracked tasks.
        """

        with self._task_tracker_lock:
            return self._num_tasks

    def _get_task_timeouts(self, task: CeleryAsyncWorkerTask) -> tuple[float, float]:
        """
        Retrieves the soft and hard time limits for the given task.

        This method calculates the appropriate soft and hard time limits for
        a Celery task, based on either its specific configuration or fallback
        to global task configuration set in the Celery app. It ensures that
        the hard limit always exceeds the soft limit by applying adjustments
        if necessary.

        :param task: The task whose time limits are to be retrieved.
        :return: A tuple containing the soft time limit and the hard time limit.
        """

        soft_limit = task.soft_time_limit or self.wsgi_app.celery.conf.task_soft_time_limit
        hard_limit = task.time_limit or self.wsgi_app.celery.conf.task_time_limit

        # Adjust limits to protect integrity: Hard limit must always be greater than Soft limit
        if soft_limit and hard_limit and soft_limit >= hard_limit:
            soft_limit = hard_limit * 0.8  # Fallback safety buffer

        return soft_limit, hard_limit

    async def _run_task_with_soft_timeout(
        self, task: CeleryAsyncWorkerTask, *args, **kwargs
    ) -> tuple[asyncio.Task | None, Any]:
        """
        Executes a task asynchronously while adhering to a soft timeout limit.

        The method ensures task execution occurs within the given soft timeout limits.
        If the task exceeds the soft time limit, it is canceled appropriately, potentially raising
        an exception within the running task, allowing custom handling in the task itself.

        :param task: The Celery task to execute asynchronously.
        :param *args: Positional arguments to pass to the task upon execution.
        :param **kwargs: Keyword arguments to pass to the task upon execution.
        :return: A tuple where the first element is an asyncio.Task instance representing the execution
                task if created, or None if it wasn't created. The second element is the result of the
                task execution, or None if the task was canceled or failed.
        :raises AssertionError: if the event loop is not ready (self._loop is None).
        :raises asyncio.TimeoutError: internally by asyncio when the soft time limit is exceeded.
        """

        assert self._loop is not None, "Event loop is not ready"
        execution_task: asyncio.Task | None = None

        async with self.wsgi_app.app_context():
            try:

                async def _run():
                    task_result = task.run(*args, **kwargs)
                    if isawaitable(task_result):
                        task_result = await task_result

                    return task_result

                if not isinstance(task, CeleryAsyncWorkerTask):
                    return None, await _run()

                soft_limit, hard_limit = self._get_task_timeouts(task)
                if not soft_limit:
                    return None, await _run()

                # Create a asyncio.Task for this, which allows us to inject exceptions into it later
                execution_task = self._loop.create_task(_run())
                self._push_task(execution_task)

                try:
                    return execution_task, await asyncio.wait_for(
                        asyncio.shield(execution_task),  # shield protects the task from cancellation
                        timeout=soft_limit,
                    )
                except asyncio.TimeoutError:
                    logger.warning("Task soft time limit exceeded", extra={"task": task.name})
                    if execution_task:
                        # This allows try/except SoftTimeLimitExceeded blocks INSIDE your task to run!
                        # This safely forces the exception directly into the running task frame
                        execution_task.cancel(SoftTimeLimitExceeded("Task soft time limit exceeded."))
                        return execution_task, await execution_task

                    return None, None
            finally:
                self._pop_task(execution_task)

    async def run_task(self, task: CeleryAsyncWorkerTask, *args, **kwargs):
        """
        Runs a Celery asynchronous worker task with optional soft and/or hard timeouts.

        If a hard timeout is not specified, the task will only be monitored with a soft
        timeout. Otherwise, the task will be executed within the specified hard timeout
        limit. If the task exceeds the hard timeout, a TimeLimitExceeded exception will
        be raised.

        :param task: The Celery task to be executed asynchronously.
        :param *args: Positional arguments to pass to the task upon execution.
        :param **kwargs: Keyword arguments to pass to the task upon execution.
        :return: The result of the task execution.
        :raises TimeLimitExceeded: If the task execution exceeds its hard time limit.
        """

        _, hard_limit = self._get_task_timeouts(task)

        if not hard_limit:
            return await self._run_task_with_soft_timeout(task, *args, **kwargs)
        else:
            try:
                return await asyncio.wait_for(
                    self._run_task_with_soft_timeout(task, *args, **kwargs), timeout=hard_limit
                )
            except asyncio.TimeoutError:
                raise TimeLimitExceeded("Task hard time limit exceeded.")

    def submit_to_thread(self, task: CeleryAsyncWorkerTask, *args, **kwargs):
        """
        Submits a task to be run in the thread using its event loop.

        This method accepts a task along with its arguments and submits it to be
        executed in the event loop after ensuring the loop is ready and the number
        of active tasks does not exceed the defined limit.

        If the thread has too many tasks currently running, this method will wait synchronously
        until the number of tasks drops below the restart threshold.

        :param task: The task to be executed.
        :param *args: Positional arguments to be passed to the task.
        :param **kwargs:Keyword arguments to be passed to the task.
        """

        self._loop_ready.wait()
        assert self._loop is not None, "Event loop is not ready"
        self.limit_active_tasks()
        thread_future = asyncio.run_coroutine_threadsafe(self.run_task(task, *args, **kwargs), loop=self._loop)
        thread_future.add_done_callback(task.on_task_complete)
        return thread_future

    def limit_active_tasks(self):
        """
        Limits the number of active tasks to prevent overload.

        This method monitors the number of currently active tasks and ensures it
        does not exceed the maximum permissible threshold. If the number of active
        tasks exceeds the threshold, it briefly halts further task execution and
        waits for the task queue size to reduce to a stable level.
        """

        num_tasks = self._get_num_tasks()
        if num_tasks < self._max_tasks:
            return

        logger.warning(f"Celery high load detected ({num_tasks}). Waiting for tasks to finish")
        while True:
            sleep(self._monitor_sleep)
            num_tasks = self._get_num_tasks()
            if num_tasks <= self._restart_tasks:
                logger.info(f"Load stabilized, task queue size reduced to {num_tasks}")
                break

    def stop(self):
        """
        Stops the running event loop if it is active and waits for the corresponding thread
        to finish execution.
        """

        if self._loop is None or not self._loop.is_running():
            return

        self._cleanup()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.join()

    def _cleanup(self, timeout: float = 10):
        """
        Cleans up any background tasks associated with the running event loop.

        This method ensures that pending asyncio tasks in the specified loop
        are properly terminated. If desired, the tasks can be cancelled before
        the cleanup process waits for their completion. It provides timeout
        functionality to limit the waiting period for task termination, ensuring
        that hanging tasks are logged and managed without indefinite blocking.

        :param timeout: The maximum time, in seconds, to wait for background tasks to finish.
        """

        if self._loop is None or not self._loop.is_running():
            return

        pending = asyncio.all_tasks(loop=self._loop)

        if not pending:
            return

        async def _async_stop():
            try:
                await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=timeout)
            except asyncio.TimeoutError:
                still_running = [t for t in pending if not t.done()]
                logger.warning(
                    f"Background task shutdown timed out. {len(still_running)} tasks still active, cancelling them now."
                )
                for task in still_running:
                    task.cancel()
                await asyncio.gather(*still_running, return_exceptions=True)
            finally:
                pass

        cleanup_future = asyncio.run_coroutine_threadsafe(_async_stop(), loop=self._loop)
        try:
            cleanup_future.result()
        except Exception:
            logger.exception("Error during background tasks shutdown")

from typing import Any, Protocol, TYPE_CHECKING, Callable
import logging
import asyncio
import threading
from inspect import isawaitable
from time import sleep

import celery
from quart import has_app_context
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

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="CeleryAsyncWorkerThread",
            daemon=True,
            **(kwargs or {}),
        )
        import superdesk

        assert superdesk.app is not None, "Superdesk app is not initialized"
        self.wsgi_app = superdesk.app

        self._max_tasks = self.wsgi_app.config.get("CELERY_ASYNC_THREAD_MAX_TASKS", 100)
        self._restart_tasks = self.wsgi_app.config.get("CELERY_ASYNC_THREAD_RESTART_TASKS", 20)
        self._monitor_sleep = self.wsgi_app.config.get("CELERY_ASYNC_THREAD_BLOCK_SLEEP", 1)

    @classmethod
    def get_instance(cls) -> "CeleryAsyncWorkerThread":
        """
        Provides a thread-safe singleton instance of CeleryAsyncWorkerThread. Ensures that only one
        instance of the worker thread exists and starts the thread if it is not already alive.

        This method is used to manage the lifecycle of the worker thread and provides
        a consistent entry point for acquiring an instance.

        :return: The singleton instance of the CeleryAsyncWorkerThread.
        """

        if not hasattr(cls._thread_local, "worker") or not cls._thread_local.worker.is_alive():
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

    async def run_task(self, task: Callable | celery.Task, *args, **kwargs) -> Any:
        """
        Executes a given task asynchronously, ensuring proper handling of app context
        and task execution lifecycle. Supports integration with Celery tasks.

        :param task: The task to execute. It can be either a standard coroutine or a Celery task.
        :param *args: Positional arguments to pass to the task upon execution.
        :param **kwargs: Keyword arguments to pass to the task upon execution.
        :return: The result of the task execution.
        """

        if not has_app_context():
            await self.wsgi_app.app_context().push()

        try:
            self._num_tasks += 1
            if isinstance(task, celery.Task):
                result = task.run(*args, **kwargs)
                if isawaitable(result):
                    result = await result
                task.backend.mark_as_done(task.request.id, result)
                return result
            else:
                return await task if isawaitable(task) else task
        except self.app_errors as e:
            logger.exception("Error running Celery task")
            if isinstance(task, celery.Task):
                task.backend.mark_as_failure(task.request.id, e)

            return None
        finally:
            self._num_tasks -= 1

    def submit(self, task: Callable | celery.Task, *args, **kwargs):
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
        result = self.run_task(task, *args, **kwargs)
        return asyncio.run_coroutine_threadsafe(result, loop=self._loop)

    def limit_active_tasks(self):
        """
        Limits the number of active tasks to prevent overload.

        This method monitors the number of currently active tasks and ensures it
        does not exceed the maximum permissible threshold. If the number of active
        tasks exceeds the threshold, it briefly halts further task execution and
        waits for the task queue size to reduce to a stable level.
        """

        if self._num_tasks < self._max_tasks:
            return

        logger.warning(f"Celery high load detected ({self._num_tasks}). Waiting for tasks to finish")
        while True:
            sleep(self._monitor_sleep)
            if self._num_tasks < self._restart_tasks:
                logger.info(f"Load stabilized, task queue size reduced to {self._num_tasks}")
                break

    def stop(self):
        """
        Stops the running event loop if it is active and waits for the corresponding thread
        to finish execution.
        """

        if self._loop is None or not self._loop.is_running():
            return

        self._loop.call_soon_threadsafe(self._loop.stop)
        self.join()

    def _cleanup(self, timeout: float = 10, cancel_tasks: bool = False):
        """
        Cleans up any background tasks associated with the running event loop.

        This method ensures that pending asyncio tasks in the specified loop
        are properly terminated. If desired, the tasks can be cancelled before
        the cleanup process waits for their completion. It provides timeout
        functionality to limit the waiting period for task termination, ensuring
        that hanging tasks are logged and managed without indefinite blocking.

        :param timeout: The maximum time, in seconds, to wait for background tasks to finish.
        :param cancel_tasks: Whether to send cancellation signals to tasks before waiting for them to terminate.
        """

        if self._loop is None or not self._loop.is_running():
            return

        pending = asyncio.all_tasks(loop=self._loop)

        if not pending:
            return

        if cancel_tasks:
            for task in pending:
                task.cancel()

        async def _async_stop():
            try:
                await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=timeout)
            except asyncio.TimeoutError:
                still_running = [t for t in pending if not t.done()]
                logger.warning(f"Background tasks shutdown timed out. {len(still_running)} tasks still active.")
                self._cleanup(timeout, cancel_tasks=True)
            finally:
                pass

        cleanup_future = asyncio.run_coroutine_threadsafe(_async_stop(), loop=self._loop)
        try:
            cleanup_future.result()
        except Exception:
            logger.exception("Error during background tasks shutdown")


class CeleryAsyncWorkerTask(HybridAppContextWorkerTask):
    def __call__(self, *args, **kwargs):
        """Executes the task function, determining if it should be run in this thread or the celery process."""

        celery_async_thread = CeleryAsyncWorkerThread.get_instance()
        if self._is_always_eager():
            return celery_async_thread.run_task(self, *args, **kwargs)
        else:
            return celery_async_thread.submit(self, *args, **kwargs)

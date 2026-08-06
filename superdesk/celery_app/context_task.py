import asyncio
from inspect import isawaitable
import werkzeug
from quart import has_app_context, Quart
from contextvars import ContextVar

from kombu.utils.uuid import uuid
from celery import Task
from typing import Any

from superdesk.logging import logger
from superdesk.errors import SuperdeskError
from superdesk.celery_app.serializer import CELERY_SERIALIZER_NAME

from .task_result import AsyncTaskResult


celery_wsgi_instance: ContextVar[Quart] = ContextVar("celery_wsgi_instance")


class HybridAppContextTask(Task):
    """
    A task class that supports running both synchronous and asynchronous tasks within the Flask application context.
    It handles exceptions specifically defined in `app_errors` and logs them.

    Note: For use with celery beat process
    """

    abstract = True
    serializer = CELERY_SERIALIZER_NAME
    app_errors = (SuperdeskError, werkzeug.exceptions.InternalServerError)

    def get_current_app(self):
        """
        Method that is intended to be overwritten so the module gets to use the right app
        context
        """
        from superdesk.core import get_current_app

        try:
            return celery_wsgi_instance.get()
        except LookupError:
            return get_current_app()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Executes the task function, determining if it should be run synchronously or asynchronously.

        Args:
            args: Positional arguments passed to the task function.
            kwargs: Keyword arguments passed to the task function.
        """
        return self.run_async(*args, **kwargs)

    def run_async(self, *args: Any, **kwargs: Any) -> Any:
        """
        Runs the task asynchronously, utilizing the current asyncio event loop. Captures
        and handles exceptions defined in `app_errors`.

        Args:
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            If the event loop is running, returns an asyncio.Task that represents the execution of the coroutine.
            Otherwise it runs the tasks and returns the result of the task.
        """
        is_always_eager = self._is_always_eager()

        async def _handle_run_task(func: Any, *func_args, **func_kwargs) -> Any:
            response = func(*func_args, **func_kwargs)
            return await response if isawaitable(response) else response

        # We need a wrapper to handle exceptions inside the async function because asyncio
        # does not propagate them in the same way as synchronous exceptions. This ensures that
        # all exceptions are managed and logged regardless of where they occur within the event loop
        async def wrapper() -> Any | None:
            try:
                if not has_app_context():
                    async with self.get_current_app().app_context():
                        return await _handle_run_task(self.run, *args, **kwargs)
                else:
                    return await _handle_run_task(self.run, *args, **kwargs)

            except self.app_errors as e:
                self.handle_exception(e)
                return None

        if is_always_eager:
            # No need to run it with app_context, as we should already be within an app context
            # Also no need to create async task, as the callee awaits the response anyway
            return wrapper()
        else:
            background_tasks = set()
            loop = asyncio.get_event_loop()

            # the loop might not be running even if `CELERY_TASK_ALWAYS_EAGER` is False
            if not loop.is_running():
                return loop.run_until_complete(wrapper())

            # **Important** from asyncio documentation
            # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
            # Save a reference to the result of this function, to avoid a task disappearing mid-execution.
            # The event loop only keeps weak references to tasks. A task that isn’t referenced elsewhere may get
            # garbage collected at any time, even before it’s done
            task = asyncio.create_task(wrapper())
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)
            return task

    def handle_exception(self, exc: Exception) -> None:
        """
        Logs an exception using the configured logger from `superdesk.logging`.
        """
        logger.exception(f"Error handling task: {str(exc)}")

    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: str) -> None:
        """
        Handles task failure by logging the exception within the Flask application context.
        """
        # TODO-ASYNC: Support async with ``on_failure`` method
        # async with self.get_current_app().app_context():
        self.handle_exception(exc)

    def _is_configured_always_eager(self):
        """Return the configured eager flag, independent of request binding."""
        # Prefer Celery's canonical flag because task execution can happen outside
        # the expected app-context resolution path on some runtimes.
        task_app = getattr(self, "app", None)
        if task_app is not None:
            task_conf = getattr(task_app, "conf", None)
            if task_conf is not None:
                eager_value = getattr(task_conf, "task_always_eager", None)
                if eager_value is not None:
                    return bool(eager_value)

        app = self.get_current_app()
        return bool(app.config.get("CELERY_TASK_ALWAYS_EAGER", False))

    def _is_always_eager(self):
        current_request = getattr(self, "request", None)
        if current_request is None or not getattr(current_request, "id", None):
            # If this task has not been bound to a request, then we're to process it directly
            # This can happen when the task is called directly, instead of using `.delay` or `.apply_async`
            return True

        return self._is_configured_always_eager()

    def AsyncResult(self, task_id, **kwargs):
        return AsyncTaskResult(task_id, backend=self.backend, app=self.app, **kwargs)


class HybridAppContextWorkerTask(HybridAppContextTask):
    """
    A task class that supports running both synchronous and asynchronous tasks within the Flask application context.
    It handles exceptions specifically defined in `app_errors` and logs them.

    Note: For use with celery worker and ASGI processes
    """

    async def apply_async(self, args: tuple = (), kwargs: dict | None = None, **other_kwargs) -> Any:
        """
        Schedules the task asynchronously. Awaits the result if `CELERY_TASK_ALWAYS_EAGER` is True.
        """
        # dispatch is eager based on configuration only, not on request binding
        if self._is_configured_always_eager():
            async_result = super().apply_async(args=args, kwargs=kwargs, **other_kwargs)
            eager_result = async_result.get()
            return await eager_result if isawaitable(eager_result) else eager_result

        return super().apply_async(args=args, kwargs=kwargs, task_id=uuid(), **other_kwargs)

    async def delay(self, *args, **kwargs) -> Any:
        return await self.apply_async(args, kwargs)

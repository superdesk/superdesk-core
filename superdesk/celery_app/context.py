import asyncio
import werkzeug

from celery import Task
from flask import current_app
from typing import Any, Callable, Tuple, Dict

from superdesk.logging import logger
from superdesk.errors import SuperdeskError
from superdesk.celery_app.serializer import CELERY_SERIALIZER_NAME


class HybridAppContextTask(Task):
    """
    A task class that supports running both synchronous and asynchronous tasks within the Flask application context.
    It handles exceptions specifically defined in `app_errors` and logs them.
    """

    abstract = True
    serializer = CELERY_SERIALIZER_NAME
    app_errors = (SuperdeskError, werkzeug.exceptions.InternalServerError)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Executes the task function, determining if it should be run synchronously or asynchronously.

        Args:
            args: Positional arguments passed to the task function.
            kwargs: Keyword arguments passed to the task function.
        """
        with current_app.app_context():
            task_func = self.run
            if asyncio.iscoroutinefunction(task_func):
                return self.run_async(task_func, *args, **kwargs)
            return self.run_sync(*args, **kwargs)

    def run_sync(self, *args: Any, **kwargs: Any) -> Any:
        """
        Runs the task synchronously within the App context.

        Args:
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The result of the synchronous task execution.
        """
        try:
            return super().__call__(*args, **kwargs)
        except self.app_errors as e:
            self.handle_exception(e)

    async def run_async(self, task_func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Runs the task asynchronously, utilizing the current asyncio event loop.

        Args:
            task_func: The coroutine function representing the task to be executed.
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The result of the asynchronous task execution.

        Raises:
            Captures and handles exceptions defined in `app_errors`.
        """
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                return loop.run_until_complete(task_func(*args, **kwargs))
            return await task_func(*args, **kwargs)
        except self.app_errors as e:
            self.handle_exception(e)

    def handle_exception(self, exc: Exception) -> None:
        """
        Logs an exception using the configured logger from `superdesk.logging`.
        """
        logger.exception("Error handling task: %s", str(exc))

    def on_failure(self, exc: Exception, task_id: str, args: Tuple, kwargs: Dict, einfo: str) -> None:
        """
        Handles task failure by logging the exception within the Flask application context.
        """
        with current_app.app_context():
            self.handle_exception(exc)

import asyncio
import werkzeug

from celery import Task
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

    def get_current_app(self):
        """
        Method that is intended to be overwritten so the module gets to use the right app
        context
        """
        from superdesk.core import get_current_app

        return get_current_app()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Executes the task function, determining if it should be run synchronously or asynchronously.

        Args:
            args: Positional arguments passed to the task function.
            kwargs: Keyword arguments passed to the task function.
        """
        # TODO-ASYNC: update once we are fully using Quart
        with self.get_current_app().app_context():
            task_func = self.run

            try:
                # handle async tasks if needed
                if asyncio.iscoroutinefunction(task_func):
                    return self.run_async(task_func, *args, **kwargs)

                # run sync otherwise
                return super().__call__(*args, **kwargs)
            except self.app_errors as e:
                self.handle_exception(e)

    def run_async(self, task_func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Runs the task asynchronously, utilizing the current asyncio event loop. Captures
        and handles exceptions defined in `app_errors`.

        Args:
            task_func: The coroutine function representing the task to be executed.
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            If the event loop is running, returns an asyncio.Task that represents the execution of the coroutine.
            Otherwise it runs the tasks and returns the result of the task.
        """

        loop = asyncio.get_event_loop()

        # We need a wrapper to handle exceptions inside the async function because asyncio
        # does not propagate them in the same way as synchronous exceptions. This ensures that
        # all exceptions are managed and logged regardless of where they occur within the event loop
        async def wrapper():
            try:
                return await task_func(*args, **kwargs)
            except self.app_errors as e:
                self.handle_exception(e)
                return None

        if not loop.is_running():
            return loop.run_until_complete(wrapper())

        return asyncio.create_task(wrapper())

    def handle_exception(self, exc: Exception) -> None:
        """
        Logs an exception using the configured logger from `superdesk.logging`.
        """
        logger.exception(f"Error handling task: {str(exc)}")

    def on_failure(self, exc: Exception, task_id: str, args: Tuple, kwargs: Dict, einfo: str) -> None:
        """
        Handles task failure by logging the exception within the Flask application context.
        """
        # TODO-ASYNC: update once we are fully using Quart
        with self.get_current_app().app_context():
            self.handle_exception(exc)

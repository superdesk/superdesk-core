from typing import cast, Any
import asyncio

from celery.result import AsyncResult


class AsyncTaskResult[T](AsyncResult):
    async def get_result_async(self, max_timeout: int = 1000) -> T:
        """
        Retrieves the result of an asynchronous task, waiting until the result is ready or the
        specified timeout is exceeded.

        The method polls the task's state at regular intervals, gradually increasing the delay
        between polls. If the result is not ready within the specified timeout, an asyncio.TimeoutError
        is raised. When the result becomes available, it extracts and returns the appropriate value or
        raises an exception if the result indicates an error.

        :param max_timeout: The maximum time, in seconds, to wait for the result to become ready before raising a timeout error. Defaults to 1000 seconds.
        :returns: The result of the asynchronous task. If the result is contained within a list, the method extracts and returns the appropriate value.
        :raises asyncio.TimeoutError: If the task's result is not ready within the specified timeout.
        :raises Exception: If the result represents an exception, the exception is raised directly.
        """

        delay = 0.01
        elapsed = 0.0

        while not self.ready():
            if elapsed >= max_timeout:
                raise asyncio.TimeoutError("Result not ready within the specified timeout")

            await asyncio.sleep(delay)
            elapsed += delay
            delay = min(delay * 1.1, 1.0)

        meta = self.backend.get_task_meta(self.id)
        results = meta.get("result") or []
        if isinstance(results, list):
            values = results[1:]
            result = values[0] if len(values) == 1 else values
        else:
            result = results

        if isinstance(result, Exception):
            # If the result is an exception, raise it directly in the calling Process/Thread
            raise result

        return cast(T, result)

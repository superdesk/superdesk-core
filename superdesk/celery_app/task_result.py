from typing import cast, Any, Callable
import asyncio
import time

from celery.result import AsyncResult
from redis.exceptions import TimeoutError as RedisTimeoutError, ConnectionError as RedisConnectionError

RESULT_BACKEND_ERRORS = (RedisTimeoutError, RedisConnectionError)


class AsyncTaskResult[T](AsyncResult):
    @staticmethod
    async def _backend_call[R](func: Callable[[], R], max_retries: int, deadline: float) -> R:
        """Call the result backend, retrying on Redis timeout/connection errors.

        The result is kept in the backend, so a failed read can safely be repeated.
        Stops retrying once the ``time.monotonic()`` deadline has passed.
        """
        for attempt in range(max_retries + 1):
            try:
                return func()
            except RESULT_BACKEND_ERRORS:
                if attempt == max_retries or time.monotonic() >= deadline:
                    raise
                await asyncio.sleep(min(0.1 * 2**attempt, 2.0))
        raise AssertionError("unreachable")

    async def get_result_async(self, max_timeout: int = 1000, max_retries: int = 5) -> T:
        """
        Retrieves the result of an asynchronous task, waiting until the result is ready or the
        specified timeout is exceeded.

        The method polls the task's state at regular intervals, gradually increasing the delay
        between polls. If the result is not ready within the specified timeout, an asyncio.TimeoutError
        is raised. When the result becomes available, it extracts and returns the appropriate value or
        raises an exception if the result indicates an error.

        :param max_timeout: The maximum time, in seconds, to wait for the result to become ready (wall-clock, including time spent in backend calls and retries) before raising a timeout error. Defaults to 1000 seconds.
        :param max_retries: Number of consecutive result backend (Redis) timeout/connection errors tolerated before re-raising.
        :returns: The result of the asynchronous task. If the result is contained within a list, the method extracts and returns the appropriate value.
        :raises asyncio.TimeoutError: If the task's result is not ready within the specified timeout.
        :raises Exception: If the result represents an exception, the exception is raised directly.
        """

        delay = 0.01
        deadline = time.monotonic() + max_timeout

        while not await self._backend_call(self.ready, max_retries, deadline):
            if time.monotonic() >= deadline:
                raise asyncio.TimeoutError("Result not ready within the specified timeout")

            await asyncio.sleep(delay)
            delay = min(delay * 1.1, 1.0)

        meta = await self._backend_call(lambda: self.backend.get_task_meta(self.id), max_retries, deadline)

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

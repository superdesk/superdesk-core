from typing import Any, Callable
import asyncio
import logging

logger = logging.getLogger(__name__)
_thread_tasks: set[asyncio.Task] = set()


def run_in_thread(func: Callable, *args: Any, **kwargs: Any) -> asyncio.Task:
    """Run a callable in a thread pool without awaiting it."""

    # ``asyncio.to_thread`` copies the current context, so Quart/Flask functionality should still work
    task_name = f"thread_task__{func.__module__}_{func.__qualname__}"
    coroutine = asyncio.to_thread(func, *args, **kwargs)
    task = asyncio.create_task(coroutine, name=task_name)
    _thread_tasks.add(task)
    task.add_done_callback(_handle_background_task_result)
    return task


async def wait_thread_tasks_to_complete(timeout: float = 10) -> None:
    """Wait for all background tasks to complete

    :param timeout: The maximum time to wait for the tasks to complete, in seconds.
    """

    if not _thread_tasks:
        return

    # Use a copy of the current tasks, as tasks remove themselves automatically from ``_thread_tasks``
    tasks = _thread_tasks.copy()

    try:
        # 1. Wrap the gather in a wait_for to enforce the timeout
        #    If a task is not finished by ``timeout`` seconds, it will be cancelled.
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout,
        )
    except asyncio.TimeoutError:
        # 2. Handle tasks that refused to stop in time
        cancelled_tasks = [t for t in tasks if t.cancelled()]
        logger.warning(f"Background threads shutdown timed out. {len(cancelled_tasks)} task(s) cancelled.")
    finally:
        # 3. Clear the set to release references
        _thread_tasks.clear()


def _handle_background_task_result(task: asyncio.Task[Any]) -> None:
    task_name = task.get_name()

    try:
        task.result()
    except asyncio.CancelledError:
        logger.warning("Background task was cancelled", extra={"task_name": task_name})
    except Exception:
        logger.exception("Background task failed", extra={"task_name": task_name})
    finally:
        _thread_tasks.discard(task)

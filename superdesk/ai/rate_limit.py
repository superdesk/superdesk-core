"""How often one user may run AI actions

A fixed one minute window per user, counted in Redis so every server process shares the count. A
user can get up to twice the limit through around the turn of a minute, which is fine for keeping
one user from running up the bill or exhausting the provider quota for everybody else.
"""

import asyncio
import logging
import math
import time

from quart_babel import gettext
from redis.exceptions import RedisError

from superdesk.core import get_current_app

from .config import config
from .errors import AIApiError

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60

#: Value of ``error_kind`` for a user over their limit, apart from ``rate_limit``, which is the
#: provider limiting Superdesk as a whole
TOO_MANY_RUNS = "too_many_runs"


class TooManyRunsError(AIApiError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            429,
            gettext("You have used AI actions too often. Try again in {seconds} seconds.").format(seconds=retry_after),
            TOO_MANY_RUNS,
        )
        self.retry_after = retry_after

    def to_dict(self) -> dict:
        return {**super().to_dict(), "retry_after": self.retry_after}


def _now() -> float:
    return time.time()


async def check_run_rate(user_id: str) -> None:
    """Count one run for the user, refusing it when it goes over ``AI_RATE_LIMIT_PER_MINUTE``

    The limit is not enforced when Redis cannot be reached: the limit protects the budget, and an
    outage of the cache is not a reason to stop editors from working.

    :raises TooManyRunsError: If the user has run their limit in the current minute already
    """

    limit = config.rate_limit_per_minute
    if limit <= 0:
        return

    now = _now()
    window = int(now // WINDOW_SECONDS)
    key = f"ai:runs:{user_id}:{window}"

    try:
        # The Redis client is synchronous, so it runs in a thread to keep a slow Redis from stalling
        # every other request on this worker
        count = await asyncio.to_thread(_count_run, get_current_app().redis, key)
    except RedisError:
        logger.warning("AI run rate could not be counted, the limit is not enforced", exc_info=True)
        return

    if count > limit:
        # Rounded up, so a client that waits exactly this long reaches the next window
        raise TooManyRunsError(retry_after=max(1, math.ceil(WINDOW_SECONDS - now % WINDOW_SECONDS)))


def _count_run(redis, key: str) -> int:
    pipeline = redis.pipeline()
    pipeline.incr(key)
    pipeline.expire(key, WINDOW_SECONDS * 2)
    count, _ = pipeline.execute()
    return count

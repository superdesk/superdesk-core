
import logging

from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Timer():
    """Timer instance."""

    def __init__(self, name):
        self.name = name
        self.start = datetime.now()

    def end(self):
        diff = datetime.now() - self.start
        logger.info('%s: %.3fms', self.name, diff / timedelta(milliseconds=1))


@contextmanager
def timer(name):
    """Time logging context manager.

    Usage:

        with timer('name'):
            time.sleep(5)  # something you want to measure
    """
    _timer = Timer(name)
    yield _timer
    _timer.end()

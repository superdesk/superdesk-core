import logging

from contextlib import contextmanager
from superdesk.utils import Timer

logger = logging.getLogger(__name__)


@contextmanager
def timer(name):
    """Time logging context manager.

    Usage:

        with timer('name'):
            time.sleep(5)  # something you want to measure
    """
    _timer = Timer()
    _timer.start(name)
    yield _timer
    time = _timer.stop(name)
    logger.info("%s: %.3fms", name, time * 1000)

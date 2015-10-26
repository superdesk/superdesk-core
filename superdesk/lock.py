
import mongolock

from werkzeug.local import LocalProxy
from flask import current_app as app
from superdesk.logging import logger


def _get_lock():
    """Get mongolock instance using app mongodb."""
    return mongolock.MongoLock(client=app.data.mongo.pymongo().db)


_lock = LocalProxy(_get_lock)


def lock(task, host, expire=300, timeout=None):
    """Try to lock task.

    :param task: task name
    :param host: current host id
    :param expire: lock ttl in seconds
    :param timeout: how long should it wait if task is locked
    """
    got_lock = _lock.lock(task, host, expire=expire, timeout=timeout)
    if got_lock:
        logger.info('got lock task=%s host=%s' % (task, host))
    else:
        logger.info('task locked already task=%s host=%s' % (task, host))
    return got_lock


def unlock(task, host):
    """Release lock on given task.

    Lock can be only released by host which locked it.

    :param task: task name
    :param host: current host id
    """
    logger.info('releasing lock task=%s host=%s' % (task, host))
    return _lock.release(task, host)

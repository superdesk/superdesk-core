
import os
import re
import socket

from mongolock import MongoLock
from werkzeug.local import LocalProxy
from flask import current_app as app
from superdesk.logging import logger


_lock_resource_settings = {
    'internal_resource': True,
    'versioning': False,
}


class SuperdeskMongoLock(MongoLock):
    """Superdesk MongoLock

    Change release to remove the lock instead of updating it
    so there is no need to gc that collection.
    """

    def release(self, key, owner, remove=False):
        if remove:
            return self.collection.delete_one({'_id': key, 'owner': owner})
        else:
            return super().release(key, owner)


def _get_lock():
    """Get mongolock instance using app mongodb."""
    app.register_resource('_lock', _lock_resource_settings)  # setup dummy resource for locks
    return SuperdeskMongoLock(client=app.data.mongo.pymongo('_lock').db)


_lock = LocalProxy(_get_lock)


def get_host():
    return 'hostid:{} pid:{}'.format(socket.gethostname(), os.getpid())


def lock(task, host=None, expire=300, timeout=None):
    """Try to lock task.

    :param task: task name
    :param host: current host id
    :param expire: lock ttl in seconds
    :param timeout: how long should it wait if task is locked
    """
    if not host:
        host = get_host()
    got_lock = _lock.lock(task, host, expire=expire, timeout=timeout)
    if got_lock:
        logger.debug('got lock task=%s host=%s' % (task, host))
    else:
        logger.debug('task locked already task=%s host=%s' % (task, host))
    return got_lock


def unlock(task, host=None, remove=False):
    """Release lock on given task.

    Lock can be only released by host which locked it.

    :param task: task name
    :param host: current host id
    :param remove: remove lock when unlocking
    """
    if not host:
        host = get_host()
    logger.debug('releasing lock task=%s host=%s' % (task, host))
    return _lock.release(task, host, remove)


def remove_locks():
    """
    Removes item related locks that are not in use
    :return:
    """
    result = _lock.collection.delete_many({'$or': [{'_id': re.compile('^item_move'), 'locked': False},
                                          {'_id': re.compile('^item_lock'), 'locked': False}]})
    logger.info('unused item locks deleted count={}'.format(result.deleted_count))

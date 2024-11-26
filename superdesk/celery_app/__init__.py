# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from sys import argv
import redis
from celery import Celery

from .context_task import HybridAppContextTask, HybridAppContextWorkerTask
from .serializer import CELERY_SERIALIZER_NAME, ContextAwareSerializerFactory

from superdesk.logging import logger
from superdesk.core import get_current_app, get_app_config


# custom serializer with Kombu for Celery's message serialization
serializer_factory = ContextAwareSerializerFactory(get_current_app)
serializer_factory.register_serializer(CELERY_SERIALIZER_NAME)

# If ``celery`` is in the executable path and ``beat`` is in the arguments
# then this code is running in a celery beat process
IS_BEAT_PROCESS = "celery" in argv[0] and "beat" in argv

# set up celery with our custom Task which handles async/sync tasks + app context
celery = Celery(__name__, task_cls=HybridAppContextTask if IS_BEAT_PROCESS else HybridAppContextWorkerTask)


def init_celery(app):
    celery.config_from_object(app.config, namespace="CELERY")
    app.celery = celery
    app.redis = __get_redis(app)


def add_subtask_to_progress(task_id):
    return _update_subtask_progress(task_id, total=True)


def finish_subtask_from_progress(task_id):
    return _update_subtask_progress(task_id, current=True)


def finish_task_for_progress(task_id):
    return _update_subtask_progress(task_id, done=True)


def __get_redis(app_ctx):
    """Constructs Redis Client object.

    :return: Redis Client object
    """
    redis_url = app_ctx.config["REDIS_URL"]
    try:
        return redis.from_url(redis_url)
    except ValueError as e:
        logger.warn("Failed to connect to redis using a connection string: {}".format(e))

        # Newer Redis clients will not accept 'amqp' as the scheme
        # Attempt to mock a redis scheme instead
        protocol = redis_url.split("//")[0]
        new_url = redis_url.replace(protocol, "redis:")
        return redis.from_url(new_url)


def update_key(key, flag=False, db=None):
    if db is None:
        db = get_current_app().redis

    if flag:
        crt_value = db.incr(key)
    else:
        crt_value = db.get(key)

    if crt_value:
        crt_value = int(crt_value)
    else:
        crt_value = 0

    return crt_value


def _update_subtask_progress(task_id, current=None, total=None, done=None):
    redis_db = redis.from_url(get_app_config("REDIS_URL"))
    try:
        current_key = "current_%s" % task_id
        total_key = "total_%s" % task_id
        done_key = "done_%s" % task_id

        crt_current = update_key(current_key, current, redis_db)
        crt_total = update_key(total_key, total, redis_db)
        crt_done = update_key(done_key, done, redis_db)

        if crt_done and crt_current == crt_total:
            redis_db.delete(current_key)
            redis_db.delete(crt_total)
            redis_db.delete(done_key)

        return task_id, crt_current, crt_total
    finally:
        redis_db.disconnect()

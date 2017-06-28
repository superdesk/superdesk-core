# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""
Created on May 29, 2014

@author: ioan
"""

import redis
import arrow
import werkzeug
import superdesk
from bson import ObjectId
from celery import Celery
from kombu.serialization import register
from eve.io.mongo import MongoJSONEncoder
from eve.utils import str_to_date
from flask import json, current_app as app
from superdesk.errors import SuperdeskError
from superdesk.logging import logger


celery = Celery(__name__)
TaskBase = celery.Task


def try_cast(v):
    # False and 0 are getting converted to datetime by arrow
    if v is None or isinstance(v, bool) or v is 0:
        return v

    try:
        str_to_date(v)  # try if it matches format
        return arrow.get(v).datetime  # return timezone aware time
    except:
        try:
            return ObjectId(v)
        except:
            return v


def dumps(o):
    with superdesk.app.app_context():
        return MongoJSONEncoder().encode(o)


def loads(s):
    o = json.loads(s)
    with superdesk.app.app_context():
        return serialize(o)


def serialize(o):
    if isinstance(o, list):
        return [serialize(item) for item in o]
    elif isinstance(o, dict):
        if o.get('kwargs') and not isinstance(o['kwargs'], dict):
            o['kwargs'] = json.loads(o['kwargs'])
        return {k: serialize(v) for k, v in o.items()}
    else:
        return try_cast(o)


register('eve/json', dumps, loads, content_type='application/json')


def handle_exception(exc):
    """Log exception to logger."""
    logger.exception(exc)


class AppContextTask(TaskBase):
    abstract = True
    serializer = 'eve/json'
    app_errors = (
        SuperdeskError,
        werkzeug.exceptions.InternalServerError,  # mongo layer err
    )

    def __call__(self, *args, **kwargs):
        with superdesk.app.app_context():
            try:
                return super().__call__(*args, **kwargs)
            except self.app_errors as e:
                handle_exception(e)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        with superdesk.app.app_context():
            handle_exception(exc)


celery.Task = AppContextTask


def init_celery(app):
    celery.config_from_object(app.config, namespace='CELERY')
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

    return redis.from_url(app_ctx.config['REDIS_URL'])


def update_key(key, flag=False, db=None):

    if db is None:
        db = app.redis

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
    redis_db = redis.from_url(app.config['REDIS_URL'])
    try:
        current_key = 'current_%s' % task_id
        total_key = 'total_%s' % task_id
        done_key = 'done_%s' % task_id

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

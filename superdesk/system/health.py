"""Health Check API

Use to check system status, will report "green" or "red" for each component
plus overall for "status"::

    {
        "status": "green",
        "celery": "green",
        "elastic": "green",
        "mongo": "green",
        "redis": "green"
    }

"""

import logging
import superdesk

from typing import Callable, List, Tuple
from flask import Blueprint, current_app as app


bp = Blueprint("system", __name__)
logger = logging.getLogger(__name__)


def mongo_health() -> bool:
    info = app.data.mongo.pymongo().cx.server_info()
    return bool(info["ok"])


def elastic_health() -> bool:
    health = app.data.elastic.es.cluster.health()
    return health["status"] in ("green", "yellow")


def celery_health() -> bool:
    with app.celery.connection_for_write() as conn:
        conn.connect()
        return conn.connected


def redis_health() -> bool:
    info = app.redis.info()
    return bool(info)


def human(status: bool) -> str:
    return "green" if status else "red"


checks: List[Tuple[str, Callable[[], bool]]] = [
    ("mongo", mongo_health),
    ("elastic", elastic_health),
    ("celery", celery_health),
    ("redis", redis_health),
]


@bp.route("/system/health", methods=["GET", "OPTIONS"])
def health():
    output = {
        "application_name": app.config.get("APPLICATION_NAME"),
    }

    status = True
    for key, check_func in checks:
        try:
            result = check_func()
        except Exception as err:
            logger.exception("error checking %s: %s", key, err)
            result = False
        status = status and result
        output[key] = human(result)

    output["status"] = human(status)
    return output


def init_app(app) -> None:
    superdesk.blueprint(bp, app)

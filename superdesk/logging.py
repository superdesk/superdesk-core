# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import logging.config
import yaml

from typing import Any, Mapping
from celery.signals import after_setup_logger, after_setup_task_logger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("superdesk")

# set default levels
logging.getLogger("ldap3").setLevel(logging.WARNING)
logging.getLogger("elasticsearch").setLevel(logging.ERROR)

logging.getLogger("apps").setLevel(logging.INFO)
logging.getLogger("superdesk").setLevel(logging.INFO)
logging.getLogger("content_api").setLevel(logging.INFO)


def item_msg(msg, item):
    """Return a message with item id appended.

    :param msg: Original message
    :param item: Item object
    """
    return "{} item={}".format(msg, str(item.get("_id", item.get("guid"))))


def configure_logging(file_path):
    """
    Configure logging.

    :param str file_path:
    """
    if not file_path:
        return

    try:
        with open(file_path, "r") as f:
            logging_dict = yaml.load(f, Loader=yaml.SafeLoader)

        logging.config.dictConfig(logging_dict)
    except Exception:
        logger.warn("Cannot load logging config. File: %s", file_path)


_graylog_handler: logging.Handler | None = None


def configure_graylog(config: Mapping[str, Any]) -> None:
    """
    Send logs to Graylog via GELF UDP if ``GRAYLOG_HOST`` is configured.

    The handler is added to the root logger, so it must run after :func:`configure_logging`
    which would otherwise replace root handlers. In celery workers it's also added to root
    and task loggers after celery sets them up.

    :param config: app config
    """
    global _graylog_handler

    if not config.get("GRAYLOG_HOST"):
        return

    if _graylog_handler is None:
        import graypy

        _graylog_handler = graypy.GELFUDPHandler(
            config["GRAYLOG_HOST"],
            int(config.get("GRAYLOG_PORT") or 12201),
            facility=config.get("GRAYLOG_FACILITY"),
        )
        _graylog_handler.setLevel(config.get("GRAYLOG_LEVEL") or logging.INFO)
        # short_message gets traceback appended so it's visible in Graylog message list,
        # it's also sent separately in full_message
        _graylog_handler.setFormatter(logging.Formatter("%(message)s"))
        after_setup_logger.connect(_add_graylog_handler, weak=False, dispatch_uid="superdesk_graylog")
        after_setup_task_logger.connect(_add_graylog_handler, weak=False, dispatch_uid="superdesk_graylog_task")

    _add_graylog_handler(logging.getLogger())


def _add_graylog_handler(logger: logging.Logger, **kwargs) -> None:
    if _graylog_handler is not None and _graylog_handler not in logger.handlers:
        logger.addHandler(_graylog_handler)

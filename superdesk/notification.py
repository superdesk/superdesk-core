# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk push notifications"""

from typing import Optional
import logging
import os
import json

from datetime import datetime
from flask import current_app as app
from superdesk.utils import json_serialize_datetime_objectId
from superdesk.websockets_comms import SocketMessageProducer
from superdesk.types import WebsocketMessageData, WebsocketMessageFilterConditions


logger = logging.getLogger(__name__)
exchange_name = "socket_notification"


class ClosedSocket:
    """Mimic closed socket to simplify logic when connection can't be established at first place."""

    def __init__(self):
        self.open = False

    def close(self):
        pass


def init_app(app) -> None:
    try:
        app.notification_client = SocketMessageProducer(app.config["BROKER_URL"], app.config.get("WEBSOCKET_EXCHANGE"))
    except (RuntimeError, OSError):
        # not working now, but we can try later when actually sending something
        app.notification_client = ClosedSocket()


def _create_socket_message(**kwargs) -> str:
    """Send out all kwargs as json string."""
    kwargs.setdefault("_created", datetime.utcnow().isoformat())
    kwargs.setdefault("_process", os.getpid())
    return json.dumps(kwargs, default=json_serialize_datetime_objectId)


def push_notification(name, filters: Optional[WebsocketMessageFilterConditions] = None, **kwargs):
    """Push notification to broker.

    In case connection is closed it will try to reconnect.

    :param name: event name
    :param filters: filter out websocket consumers by certain conditions
    """
    logger.debug("pushing event {0} ({1})".format(name, json.dumps(kwargs, default=json_serialize_datetime_objectId)))

    if not getattr(app, "notification_client", None):
        # not initialized - ignore
        # this could be the case for content/production api
        return

    if not app.notification_client.open:
        app.notification_client.close()
        init_app(app)

    if not app.notification_client.open:
        logger.warning("No connection to broker. Dropping event %s" % name)
        return

    try:
        msg_kwargs = WebsocketMessageData(
            event=name,
            extra=kwargs,
        )
        if filters:
            msg_kwargs["filters"] = filters

        message = _create_socket_message(**msg_kwargs)
        logger.debug("Sending the message: {} to the broker.".format(message))
        app.notification_client.send(message)
    except Exception as err:
        logger.exception(err)

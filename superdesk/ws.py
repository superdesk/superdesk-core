#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
import logging

from superdesk.websockets_comms import SocketCommunication


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_server(config):
    """Create websocket server and run it until it gets Ctrl+C or SIGTERM.

    :param config: config dictionary
    """
    try:
        host = config["WS_HOST"]
        port = int(config["WS_PORT"])
        broker_url = config["BROKER_URL"]
        exchange_name = config.get("WEBSOCKET_EXCHANGE", "superdesk_notification")
        comms = SocketCommunication(host, port, broker_url, exchange_name)
        comms.run_server()
    except Exception:
        logger.exception("Failed to start the WebSocket server.")


if __name__ == "__main__":
    config = {
        "WS_HOST": os.environ.get("WS_HOST") or "0.0.0.0",
        "WS_PORT": int(os.environ.get("WS_PORT") or "5100"),
        "BROKER_URL": os.environ.get("CELERY_BROKER_URL") or os.environ.get("REDIS_URL") or "redis://localhost:6379",
        "WEBSOCKET_EXCHANGE": "superdesk_notification",
    }

    create_server(config)

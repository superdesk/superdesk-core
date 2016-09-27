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


import logging
import logging.handlers
from superdesk.websockets_comms import SocketCommunication

logger = logging.getLogger(__name__)


def create_server(config):
    """Create websocket server and run it until it gets Ctrl+C or SIGTERM.

    :param config: config dictionary
    """
    try:
        host = config['WS_HOST']
        port = int(config['WS_PORT'])
        broker_url = config['BROKER_URL']
        comms = SocketCommunication(host, port, broker_url)
        comms.run_server()
    except:
        logger.exception('Failed to start the WebSocket server.')

if __name__ == '__main__':
    config = {
        'WS_HOST': '0.0.0.0',
        'WS_PORT': '5100',
        'BROKER_URL': 'redis://localhost:6379'
    }
    create_server(config)

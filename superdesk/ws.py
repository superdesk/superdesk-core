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
import json
import logging
import asyncio
import signal

from autobahn.asyncio.websocket import WebSocketServerProtocol
from autobahn.asyncio.websocket import WebSocketServerFactory
from logging.handlers import SysLogHandler
from logging import Formatter


beat_delay = 30


def configure_logging(config):
    debug_log_format = ('%(levelname)s:%(module)s:%(message)s\n')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = SysLogHandler(address=(config['LOG_SERVER_ADDRESS'], config['LOG_SERVER_PORT']))
    handler.setFormatter(Formatter(debug_log_format))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    return logger


def log(logger, log_msg):
    logger.info(log_msg)
    print(log_msg)


class BroadcastProtocol(WebSocketServerProtocol):
    """Client protocol - there is an instance per client connection."""

    def onOpen(self):
        """Register"""
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        """Broadcast msg from a client"""
        self.factory.broadcast(payload, self.peer)

    def connectionLost(self, reason):
        """Unregister on connection drop"""
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):
    """Server handling client registrations and broadcasting"""

    def __init__(self, logger, *args):
        WebSocketServerFactory.__init__(self, *args)
        self.clients = []
        self.logger = logger

    def register(self, client):
        """Register a client"""
        if client not in self.clients:
            log(self.logger, 'registered client {}'.format(client.peer))
            self.clients.append(client)
            client.sendMessage(json.dumps({'event': 'connected'}).encode('utf8'))

    def unregister(self, client):
        """Unregister a client"""
        if client in self.clients:
            log(self.logger, 'unregister client {}'.format(client.peer))
            self.clients.remove(client)

    def broadcast(self, msg, author):
        """Broadcast msg to all clients but author."""
        log(self.logger, 'broadcasting "{0}"'.format(msg.decode('utf8')))

        for c in self.clients:
            if c.state == c.STATE_CLOSED:
                self.unregister(c)

        for c in self.clients:
            if c.peer is not author:
                c.sendMessage(msg)
        log(self.logger, 'msg sent to {0} client(s)'.format(len(self.clients)))


def send_heartbeat(server, loop):
    yield from asyncio.sleep(beat_delay)
    while loop.is_running():
        server.broadcast(json.dumps({
            'data': 'ping',
            'from': os.environ.get('SUPERDESK_URL')
        }).encode('utf8'), None)
        yield from asyncio.sleep(beat_delay)


def create_server(config):
    logger = configure_logging(config)
    factory = BroadcastServerFactory(logger)
    factory.protocol = BroadcastProtocol

    loop = asyncio.get_event_loop()
    coro = loop.create_server(factory, config['WS_HOST'], config['WS_PORT'])
    server = loop.run_until_complete(coro)

    def stop():
        log(logger, 'closing...')
        server.close()
        loop.call_soon_threadsafe(loop.stop)

    loop.add_signal_handler(signal.SIGTERM, stop)

    try:
        log(logger, 'initializing heartbeat...')
        asyncio.async(send_heartbeat(factory, loop))

        log(logger, 'listening on {0}:{1}'.format(config['WS_HOST'], config['WS_PORT']))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop()


if __name__ == '__main__':
    config = {
        'WS_HOST': '0.0.0.0',
        'WS_PORT': '5100',
        'LOG_SERVER_ADDRESS': 'localhost',
        'LOG_SERVER_PORT': '5555'
    }
    create_server(config)

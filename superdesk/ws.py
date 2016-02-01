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


import json
import signal
import asyncio
import logging
import websockets
import logging.handlers

beat_delay = 5
clients = set()

logger = logging.getLogger(__name__)


@asyncio.coroutine
def client_loop(websocket):
    """Client loop - send it ping every `beat_delay` seconds to keep it alive.

    Nginx would close the connection after 2 minutes of inactivity, that's why.

    Also it does the health check - if socket was closed by client it will
    break the loop and let server deregister the client.

    :param websocket: websocket protocol instance
    """
    pings = 0
    while True:
        yield from asyncio.sleep(beat_delay)
        if not websocket.open:
            break
        pings += 1
        yield from websocket.send(json.dumps({'ping': pings, 'clients': len(websocket.ws_server.websockets)}))


@asyncio.coroutine
def broadcast(message):
    """Broadcast message to all clients.

    :param message: message as it was received - no encoding/decoding.
    """
    logger.debug('broadcast %s' % message)
    for websocket in clients:
        if websocket.open:
            yield from websocket.send(message)


@asyncio.coroutine
def server_loop(websocket):
    """Server loop - wait for message and broadcast it.

    When message is none it means the socket is closed
    and there will be no messages so we break the loop.

    :param websocket: websocket protocol instance
    """
    while True:
        message = yield from websocket.recv()
        if message is None:
            break
        yield from broadcast(message)


def log(message, websocket):
    """Log message with some websocket data like address.

    :param message: message string
    :param websocket: websocket protocol instance
    """
    host, port = websocket.remote_address
    logger.info('%s address=%s:%s' % (message, host, port))


@asyncio.coroutine
def connection_handler(websocket, path):
    """Handle incomming connections.

    When this function returns the session is over and it closes the socket,
    so there must be some loops..

    :param websocket: websocket protocol instance
    :param path: url path used by client - used to identify client/server connections
    """
    if 'server' in path:
        log('server open', websocket)
        yield from server_loop(websocket)
        log('server done', websocket)
    else:
        log('client open', websocket)
        clients.add(websocket)
        yield from client_loop(websocket)
        clients.remove(websocket)
        log('client done', websocket)


def create_server(config):
    """Create websocket server and run it until it gets Ctrl+C or SIGTERM.

    :param config: config dictionary
    """
    try:
        host = config['WS_HOST']
        port = int(config['WS_PORT'])
        loop = asyncio.get_event_loop()
        server = loop.run_until_complete(websockets.serve(connection_handler, host, port))
        loop.add_signal_handler(signal.SIGTERM, loop.stop)
        logger.info('listening on %s:%s' % (host, port))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info('closing server')
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.stop()
        loop.run_forever()
        loop.close()


if __name__ == '__main__':
    config = {
        'WS_HOST': '0.0.0.0',
        'WS_PORT': '5100',
    }
    create_server(config)

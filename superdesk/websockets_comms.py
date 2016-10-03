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


import arrow
import logging
import asyncio
import websockets
import signal

from datetime import timedelta
from threading import Thread
from kombu import Queue, Exchange, Connection
from kombu.mixins import ConsumerMixin
from kombu.pools import producers
from superdesk.utc import utcnow
from superdesk.utils import get_random_string
from flask import json


logger = logging.getLogger(__name__)
exchange_name = 'socket_notification'


class SocketBrokerClient:
    """
    Base class for web socket notification using broker (redis or rabbitmq)
    """

    connection = None

    def __init__(self, url):
        self.url = url
        self.connect()
        self.channel = self.connection.channel()
        self.socket_exchange = Exchange(exchange_name, type='fanout', channel=self.channel)
        self.socket_exchange.declare()

    def open(self):
        """Test if connection is open.

        True if connected else false

        :return bool:
        """
        return self.connection and self.connection.connected

    def connect(self):
        self._close()
        logger.info('Connecting to broker {}'.format(self.url))
        self.connection = Connection(self.url)
        self.connection.connect()
        logger.info('Connected to broker {}'.format(self.url))

    def _close(self):
        if hasattr(self, 'connection') and self.connection:
            logger.info('Closing connecting to broker {}'.format(self.url))
            self.connection.release()
            self.connection = None
            logger.info('Connection closed to broker {}'.format(self.url))

    def close(self):
        self._close()


class SocketMessageProducer(SocketBrokerClient):
    """
    Publishes messages to a exchange (fanout).
    """

    def __init__(self, url):
        super().__init__(url)

    def send(self, message):
        """
        Publishes the message to an exchange

        :param string message: message to publish
        """
        try:
            with producers[self.connection].acquire(block=True) as producer:
                producer.publish(message, exchange=self.socket_exchange)
                logger.debug('message:{} published to broker:{}.'.format(message, self.url))
        except:
            logger.exception('Failed to publish message {} to broker.'.format(message))


class SocketMessageConsumer(SocketBrokerClient, ConsumerMixin):
    """
    Consumer of the message.
    """

    def __init__(self, url, callback):
        """Create consumer.

        :param string url: Broker URL
        :param string host: host name running the websocket server
        :param callback: callback function to call on message arrival
        """
        super().__init__(url)
        self.callback = callback
        self.queue_name = 'socket_consumer_{}'.format(get_random_string())
        # expire message after 10 seconds and queue after 60 seconds
        self.queue = Queue(self.queue_name, exchange=self.socket_exchange,
                           channel=self.channel,
                           queue_arguments={'x-message-ttl': 10000, 'x-expires': 60000})

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[self.queue], callbacks=[self.on_message])]

    def on_message(self, body, message):
        """
        Event fired when message is received by the queue

        :param str body:
        :param kombu.Message message: Message object
        """
        try:
            try:
                loop = asyncio.get_event_loop()
            except:
                loop = asyncio.new_event_loop()

            logger.info('Queue: {}. Broadcasting message {}'.format(self.queue_name, body))
            loop.run_until_complete(self.callback(body))
        except:
            logger.exception('Dropping event. Failed to send message {}.'.format(body))
        try:
            message.ack()
        except:
            logger.exception('Failed to ack message {} on queue {}.'.format(body, self.queue_name))

    def close(self):
        """
        Closing the consumer.

        :return:
        """
        logger.info('closing consumer')
        self.should_stop = True
        super().close()
        logger.info('consumer terminated successfully')


class SocketCommunication:
    """
    Responsible for websocket comms.
    """

    clients = set()

    def __init__(self, host, port, broker_url):
        self.host = host
        self.port = port
        self.broker_url = broker_url
        self.messages = {}
        self.event_interval = {
            'ingest:update': 5,
            'ingest:cleaned': 5,
            'content:expired': 5,
            'publish_queue:update': 5,
        }

    @asyncio.coroutine
    def _client_loop(self, websocket):
        """Client loop - send it ping every `beat_delay` seconds to keep it alive.

        Nginx would close the connection after 2 minutes of inactivity, that's why.

        Also it does the health check - if socket was closed by client it will
        break the loop and let server deregister the client.

        :param websocket: websocket protocol instance
        """
        pings = 0
        while True:
            yield from asyncio.sleep(5)
            if not websocket.open:
                break
            pings += 1
            yield from websocket.send(json.dumps({'ping': pings, 'clients': len(websocket.ws_server.websockets)}))

    @asyncio.coroutine
    def broadcast(self, message):
        """Broadcast message to all clients.

        If event is in `event_interval` it will only send such event every x seconds.

        :param message: message as it was received - no encoding/decoding.
        """
        message_data = json.loads(message)
        message_id = message_data.get('event', '')
        message_created = arrow.get(message_data.get('_created', utcnow()))
        last_created = self.messages.get(message_id)
        ttl = self.event_interval.get(message_id, 0)

        if last_created and last_created + timedelta(seconds=ttl) > message_created:
            logger.info('skiping event %s' % (message_id, ))
            return

        if ttl:
            self.messages[message_id] = message_created

        logger.debug('broadcast %s' % message)
        for websocket in self.clients.copy():
            try:
                if websocket.open:
                    yield from websocket.send(message)
            except:
                yield

    @asyncio.coroutine
    def _server_loop(self, websocket):
        """Server loop - wait for message and broadcast it.

        When message is none it means the socket is closed
        and there will be no messages so we break the loop.

        :param websocket: websocket protocol instance
        """
        while True:
            message = yield from websocket.recv()
            if message is None:
                break
            yield from self.broadcast(message)

    def _log(self, message, websocket):
        """Log message with some websocket data like address.

        :param message: message string
        :param websocket: websocket protocol instance
        """
        host, port = websocket.remote_address
        logger.info('%s address=%s:%s' % (message, host, port))

    @asyncio.coroutine
    def _connection_handler(self, websocket, path):
        """Handle incomming connections.

        When this function returns the session is over and it closes the socket,
        so there must be some loops..

        :param websocket: websocket protocol instance
        :param path: url path used by client - used to identify client/server connections
        """
        if 'server' in path:
            self._log('server open', websocket)
            yield from self._server_loop(websocket)
            self._log('server done', websocket)
        else:
            self._log('client open', websocket)
            self.clients.add(websocket)
            yield from self._client_loop(websocket)
            self.clients.remove(websocket)
            self._log('client done', websocket)

    def run_server(self):
        """Create websocket server and run it until it gets Ctrl+C or SIGTERM.

        :param config: config dictionary
        """
        try:
            loop = asyncio.get_event_loop()
            server = loop.run_until_complete(websockets.serve(self._connection_handler,
                                                              self.host, self.port))
            loop.add_signal_handler(signal.SIGTERM, loop.stop)
            logger.info('listening on %s:%s' % (self.host, self.port))
            consumer = None
            # create socket message consumer
            consumer = SocketMessageConsumer(self.broker_url, self.broadcast)
            consumer_thread = Thread(target=consumer.run)
            consumer_thread.start()
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
            if consumer:
                consumer.close()

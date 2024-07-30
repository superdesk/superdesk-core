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
import signal
import websockets

from uuid import UUID
from urllib.parse import urlparse, parse_qs
from websockets.server import WebSocketServerProtocol
from typing import Dict, Set, Optional, Union
from superdesk.types import WebsocketMessageData, WebsocketMessageFilterConditions

from datetime import timedelta, datetime
from threading import Thread
from kombu import Queue, Exchange, Connection
from kombu.mixins import ConsumerMixin
from kombu.pools import producers
from superdesk.core import json
from superdesk.utc import utcnow
from superdesk.utils import get_random_string, json_serialize_datetime_objectId
from superdesk.default_settings import WS_HEART_BEAT


logger = logging.getLogger(__name__)


class SocketBrokerClient:
    """
    Base class for web socket notification using broker (redis or rabbitmq)
    """

    url: str
    exchange_name: str
    connection: Connection
    socket_exchange: Exchange

    def __init__(self, url, exchange_name):
        self.url = url
        self.connect()
        self.exchange_name = exchange_name
        self.socket_exchange = Exchange(self.exchange_name, type="fanout")

    def open(self):
        """Test if connection is open.

        True if connected else false

        :return bool:
        """
        return self.connection and self.connection.connected

    def connect(self):
        self._close()
        logger.info("Connecting to broker {}".format(self.url))
        self.connection = Connection(self.url, heartbeat=WS_HEART_BEAT)
        logger.info("Connected to broker {}".format(self.url))

    def _close(self):
        if hasattr(self, "connection") and self.connection:
            logger.info("Closing connecting to broker {}".format(self.url))
            self.connection.release()
            logger.info("Connection closed to broker {}".format(self.url))

    def close(self):
        self._close()


class SocketMessageProducer(SocketBrokerClient):
    """Used by backeend processes to send messages."""

    def send(self, message):
        """
        Publishes the message to an exchange

        :param string message: message to publish
        """
        try:
            with producers[self.connection].acquire(block=True) as producer:
                producer.publish(message, exchange=self.socket_exchange, declare=[self.socket_exchange], retry=True)
                logger.debug("message %s published to broker=%s exchange=%s.", message, self.url, self.socket_exchange)
        except Exception:
            logger.exception("Failed to publish message {} to broker.".format(message))


class SocketMessageConsumer(SocketBrokerClient, ConsumerMixin):
    """
    Consumer of the message.
    """

    queue: Queue

    def __init__(self, url, callback, exchange_name):
        """Create consumer.

        :param string url: Broker URL
        :param string host: host name running the websocket server
        :param callback: callback function to call on message arrival
        """
        super().__init__(url, exchange_name)
        self.callback = callback
        self.queue_name = "websocket_queue_{}".format(get_random_string())
        self.queue = Queue(
            self.queue_name,
            exchange=self.socket_exchange,
            message_ttl=10,
            expires=60,
            channel=self.connection.channel(),
            exclusive=True,
        )

        logger.info("Websocket queue created %s", self.queue_name)

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
            except Exception:
                loop = asyncio.new_event_loop()

            logger.info("Queue: {}. Broadcasting message {}".format(self.queue_name, body))
            loop.run_until_complete(self.callback(body))
        except Exception:
            logger.exception("Dropping event. Failed to send message {}.".format(body))
        try:
            message.ack()
        except Exception:
            logger.exception("Failed to ack message {} on queue {}.".format(body, self.queue_name))

    def close(self):
        """
        Closing the consumer.

        :return:
        """
        logger.info("closing consumer")
        self.should_stop = True
        super().close()
        logger.info("consumer terminated successfully")


class SocketCommunication:
    """
    Responsible for websocket comms.
    """

    clients: Set[WebSocketServerProtocol] = set()

    def __init__(
        self,
        host: str,
        port: Union[int, str],
        broker_url: str,
        exchange_name: Optional[str] = None,
        subscribe_prefix: str = "/subscribe?",
    ):
        self.host = host
        self.port = port
        self.broker_url = broker_url
        self.exchange_name = exchange_name
        self.subscribe_prefix = subscribe_prefix
        self.client_url_args: Dict[UUID, Dict[str, str]] = {}
        self.messages: Dict[str, datetime] = {}
        self.event_interval = {
            "ingest:update": 5,
            "ingest:cleaned": 5,
            "content:expired": 5,
            "publish_queue:update": 5,
        }

    def _add_client(self, websocket: WebSocketServerProtocol):
        self.clients.add(websocket)

        # Store client URL args for use with message filters
        if self.subscribe_prefix not in websocket.path:
            self.client_url_args[websocket.id] = {}
        else:
            parsed_url = urlparse(websocket.path)
            url_params = parse_qs(parsed_url.query)
            self.client_url_args[websocket.id] = {key: val[0] for key, val in url_params.items()}

    def _remove_client(self, websocket: WebSocketServerProtocol):
        self.clients.remove(websocket)
        self.client_url_args.pop(websocket.id, None)

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
            yield from websocket.send(json.dumps({"ping": pings, "clients": len(websocket.ws_server.websockets)}))

    def get_message_recipients(self, message_data: WebsocketMessageData) -> Set[WebSocketServerProtocol]:
        """Filter consumers by message filter attributes

        When client's connect, they can provide a set of URL arguments as to what they need to subscribe to
        Such as specific user and/or company combination.
        These URL arguments are then checked against the filter conditions in the ``message_data``
        to determine which clients this ``message_data`` is to be sent to
        """

        clients = self.clients.copy()

        if not message_data.get("filters"):
            return clients

        filters: WebsocketMessageFilterConditions = message_data.pop("filters", {})
        filters.setdefault("include", {})
        filters.setdefault("exclude", {})

        if not filters["include"] and not filters["exclude"]:
            return clients

        def _filter(websocket: WebSocketServerProtocol) -> bool:
            url_args = self.client_url_args.get(websocket.id) or {}
            if filters["include"] and not url_args:
                # If ``filter.include`` is defined, client must provide url args in websocket path
                # as we're explicitly including only clients that have args in this list
                return False

            try:
                for key, values in filters["include"].items():
                    if url_args.get(key) not in values:
                        return False

                for key, values in filters["exclude"].items():
                    if url_args.get(key) in values:
                        return False
            except (KeyError, ValueError, IndexError):
                return False

            return True

        return set(filter(_filter, clients))

    @asyncio.coroutine
    def broadcast(self, message):
        """Broadcast message to all clients.

        If event is in `event_interval` it will only send such event every x seconds.

        :param message: message as it was received - no encoding/decoding.
        """
        message_data = json.loads(message)
        message_id = message_data.get("event", "")
        message_created = arrow.get(message_data.get("_created", utcnow()))
        last_created = self.messages.get(message_id)
        ttl = self.event_interval.get(message_id, 0)

        if last_created and last_created + timedelta(seconds=ttl) > message_created:
            logger.info("skiping event %s" % (message_id,))
            return

        if ttl:
            self.messages[message_id] = message_created

        logger.debug("broadcast %s" % message)
        for websocket in self.get_message_recipients(message_data):
            try:
                if websocket.open:
                    # Reconstruct the message string
                    # as not to send the ``message.filter`` dictionary to clients
                    yield from websocket.send(json.dumps(message_data, default=json_serialize_datetime_objectId))
            except Exception:
                yield

    @asyncio.coroutine
    def _server_loop(self, websocket):
        """Server loop - wait for message and broadcast it.

        :param websocket: websocket protocol instance
        """
        while True:
            message = yield from websocket.recv()
            yield from self.broadcast(message)

    def _log(self, message, websocket):
        """Log message with some websocket data like address.

        :param message: message string
        :param websocket: websocket protocol instance
        """
        host, port = websocket.remote_address
        logger.info("%s address=%s:%s" % (message, host, port))

    @asyncio.coroutine
    def _connection_handler(self, websocket, path):
        """Handle incomming connections.

        When this function returns the session is over and it closes the socket,
        so there must be some loops..

        :param websocket: websocket protocol instance
        :param path: url path used by client - used to identify client/server connections
        """
        if "server" in path:
            self._log("server open", websocket)
            yield from self._server_loop(websocket)
            self._log("server done", websocket)
        else:
            self._log("client open", websocket)
            self._add_client(websocket)
            yield from self._client_loop(websocket)
            self._remove_client(websocket)
            self._log("client done", websocket)

    def run_server(self):
        """Create websocket server and run it until it gets Ctrl+C or SIGTERM.

        :param config: config dictionary
        """
        try:
            loop = asyncio.get_event_loop()
            server = loop.run_until_complete(websockets.serve(self._connection_handler, self.host, self.port))
            loop.add_signal_handler(signal.SIGTERM, loop.stop)
            logger.info("listening on %s:%s" % (self.host, self.port))
            consumer = None
            # create socket message consumer
            consumer = SocketMessageConsumer(self.broker_url, self.broadcast, self.exchange_name)
            consumer_thread = Thread(target=consumer.run)
            consumer_thread.start()
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("closing server")
            server.close()
            loop.run_until_complete(server.wait_closed())
            loop.stop()
            loop.run_forever()
            loop.close()
            if consumer:
                consumer.close()

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
import sentry_sdk

from uuid import UUID, uuid1
from urllib.parse import urlparse, parse_qs
from websockets.asyncio.server import ServerConnection, broadcast, serve
from typing import Dict, Set, Optional, Union
from superdesk.types import WebsocketMessageData, WebsocketMessageFilterConditions
from sentry_sdk.consts import SPANSTATUS
from sentry_sdk.integrations.asyncio import AsyncioIntegration

from datetime import timedelta, datetime
from kombu import Queue, Exchange, Connection
from kombu.mixins import ConsumerMixin
from kombu.pools import producers

from superdesk.core import json

from kombu.common import Broadcast
from kombu.utils.debug import setup_logging


from superdesk.utc import utcnow
from superdesk.utils import get_random_string, json_serialize_datetime_objectId
from superdesk.default_settings import WS_HEART_BEAT


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logging.getLogger("websockets").setLevel(logging.WARNING)
setup_logging(logging.WARNING)


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

    def send(self, message: str, name: str):
        """
        Publishes the message to an exchange

        :param string message: message to publish
        """
        with sentry_sdk.start_span(op="queue.publish", name=name) as span:
            _id = uuid1().hex
            span.set_data("messaging.message.id", _id)
            span.set_data("messaging.destination.name", self.exchange_name)
            span.set_data("messaging.message.body.size", len(message))

            try:
                with producers[self.connection].acquire(block=True) as producer:
                    producer.publish(
                        message,
                        exchange=self.socket_exchange,
                        declare=[self.socket_exchange],
                        retry=True,
                        headers={
                            "sentry-trace": sentry_sdk.get_traceparent(),
                            "baggage": sentry_sdk.get_baggage(),
                            "message-id": _id,
                        },
                    )
                    logger.debug(
                        "message %s published to broker=%s exchange=%s.", message, self.url, self.socket_exchange
                    )
                    span.set_status(SPANSTATUS.OK)
            except Exception:
                logger.exception("Failed to publish message {} to broker.".format(message))
                span.set_status(SPANSTATUS.INTERNAL_ERROR)


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

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[self.queue], callbacks=[self.on_message])]

    def on_message(self, body, message):
        """
        Event fired when message is received by the queue

        :param str body:
        :param kombu.Message message: Message object
        """
        transaction = sentry_sdk.continue_trace(
            message.headers,
            op="function",
            name="queue_consumer_transaction",
        )
        with sentry_sdk.start_transaction(transaction):
            logger.debug("Queue: {}. Broadcasting message {}".format(self.queue.name, body))
            with sentry_sdk.start_span(op="queue.process", name="queue_consumer") as span:
                span.set_data("messaging.message.id", message.headers["message-id"])
                span.set_data("messaging.destination.name", self.exchange_name)
                span.set_data("messaging.message.body.size", len(body))
                try:
                    self.callback(body)
                    message.ack()
                    span.set_status(SPANSTATUS.OK)
                    transaction.set_status(SPANSTATUS.OK)
                except Exception:
                    logger.exception("Error when receiving message.")
                    span.set_status(SPANSTATUS.INTERNAL_ERROR)
                    transaction.set_status(SPANSTATUS.INTERNAL_ERROR)

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

    clients: Set[ServerConnection]

    def __init__(
        self,
        host: str,
        port: Union[int, str],
        broker_url: str,
        exchange_name: Optional[str] = None,
        subscribe_prefix: str = "/subscribe?",
        *,
        sentry_dsn: Optional[str] = None,
        sentry_traces_sample_rate: Optional[float] = None,
        debug: bool = False,
    ):
        self.host = host
        self.port = int(port)
        self.broker_url = broker_url
        self.exchange_name = exchange_name
        self.subscribe_prefix = subscribe_prefix
        self.client_url_args: Dict[UUID, Dict[str, str]] = {}
        self.messages: Dict[str, datetime] = {}
        self.clients = set()
        self.event_interval = {
            "ingest:update": 5,
            "ingest:cleaned": 5,
            "content:expired": 5,
            "publish_queue:update": 5,
        }
        self.sentry_dsn = sentry_dsn
        self.sentry_traces_sample_rate = sentry_traces_sample_rate
        self.debug = debug

    def _add_client(self, websocket: ServerConnection):
        self.clients.add(websocket)

        path = websocket.request.path if websocket.request else ""

        # Store client URL args for use with message filters
        if self.subscribe_prefix not in path:
            self.client_url_args[websocket.id] = {}
        else:
            parsed_url = urlparse(path)
            url_params = parse_qs(parsed_url.query)
            self.client_url_args[websocket.id] = {key: val[0] for key, val in url_params.items()}

    def _remove_client(self, websocket: ServerConnection):
        self.clients.remove(websocket)
        self.client_url_args.pop(websocket.id, None)

    async def _client_loop(self, websocket: ServerConnection):
        """Client loop - noop.

        :param websocket: websocket protocol instance
        """
        await websocket.wait_closed()

    def get_message_recipients(self, message_data: WebsocketMessageData) -> Set[ServerConnection]:
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

        def _filter(websocket: ServerConnection) -> bool:
            url_args = self.client_url_args.get(websocket.id) or {}
            if filters.get("include") and not url_args:
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
        clients = self.get_message_recipients(message_data)
        broadcast(clients, json.dumps(message_data, default=json_serialize_datetime_objectId))

    def _log(self, message: str, websocket: ServerConnection):
        """Log message with some websocket data like address.

        :param message: message string
        :param websocket: websocket protocol instance
        """
        host, port = websocket.remote_address
        logger.info("%s address=%s:%s" % (message, host, port))

    async def _connection_handler(self, websocket: ServerConnection):
        """Handle incomming connections.

        When this function returns the session is over and it closes the socket,
        so there must be some loops..

        :param websocket: websocket protocol instance
        :param path: url path used by client - used to identify client/server connections
        """
        self._log("client open", websocket)
        self._add_client(websocket)
        try:
            await self._client_loop(websocket)
        finally:
            self._remove_client(websocket)
            self._log("client done", websocket)

    def run_server(self):
        """Run websocket server."""
        asyncio.run(self.main())

    async def main(self):
        """Create websocket server and run it until it gets Ctrl+C or SIGTERM."""
        if self.sentry_dsn:
            sentry_sdk.init(
                self.sentry_dsn,
                integrations=[AsyncioIntegration()],
                traces_sample_rate=self.sentry_traces_sample_rate,
                debug=self.debug,
            )
            print("CONFIGURED", self.sentry_traces_sample_rate)
        else:
            print("NOT CONFIGURED", self.sentry_dsn, self.sentry_traces_sample_rate)
        try:
            consumer = None
            async with serve(self._connection_handler, self.host, self.port) as server:
                loop = asyncio.get_event_loop()
                loop.add_signal_handler(signal.SIGTERM, server.close)
                # create socket message consumer
                consumer = SocketMessageConsumer(self.broker_url, self.broadcast, self.exchange_name)
                # kombu is blocking so needs to run in executor
                loop.run_in_executor(None, consumer.run)
                await server.wait_closed()
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("closing server")
            if consumer:
                consumer.close()

from typing import List
import asyncio
import unittest
from unittest.mock import MagicMock, patch, ANY
from json import dumps
from datetime import datetime, timedelta
from uuid import uuid4
from superdesk.websockets_comms import SocketCommunication
from superdesk.types import WebsocketMessageData
from websockets import ServerConnection, ServerProtocol
from websockets.protocol import OPEN


class TestClient(ServerConnection):
    def __init__(self, path: str):
        self.id = uuid4()
        self.request = MagicMock()
        self.request.path = path


class WebsocketsTestCase(unittest.TestCase):
    @patch("superdesk.websockets_comms.broadcast")
    def test_broadcast(self, broadcast_mock):
        client = TestClient("")
        com = SocketCommunication("host", "1", "url")
        com.clients.add(client)

        com.broadcast(dumps({"event": "ingest:update", "_created": datetime.now().isoformat()}))
        self.assertEqual(1, broadcast_mock.call_count)

        com.broadcast(dumps({"event": "ingest:update", "_created": datetime.now().isoformat()}))
        self.assertEqual(1, broadcast_mock.call_count)

        com.broadcast(dumps({"event": "foo", "_created": datetime.now().isoformat()}))
        self.assertEqual(2, broadcast_mock.call_count)

        com.broadcast(dumps({"event": "foo", "_created": datetime.now().isoformat()}))
        self.assertEqual(3, broadcast_mock.call_count)

        com.broadcast(
            dumps({"event": "ingest:update", "_created": (datetime.now() + timedelta(seconds=3600)).isoformat()})
        )
        self.assertEqual(4, broadcast_mock.call_count)

    @patch("superdesk.websockets_comms.broadcast")
    def test_broadcast_specific_recipients(self, broadcast_mock):
        client_no_user = TestClient("")
        client_user_abc123_sess_12345 = TestClient("/ws/subscribe?user=abc123&session=12345")
        client_user_abc123_sess_67890 = TestClient("/ws/subscribe?user=abc123&session=67890")
        client_user_def456 = TestClient("/ws/subscribe?user=def456")

        com = SocketCommunication("host", "1", "url")
        com._add_client(client_no_user)
        com._add_client(client_user_abc123_sess_12345)
        com._add_client(client_user_abc123_sess_67890)
        com._add_client(client_user_def456)

        # Test stored client URL args
        self.assertEqual(com.client_url_args[client_no_user.id], {})
        self.assertEqual(com.client_url_args[client_user_abc123_sess_12345.id], {"user": "abc123", "session": "12345"})
        self.assertEqual(com.client_url_args[client_user_abc123_sess_67890.id], {"user": "abc123", "session": "67890"})
        self.assertEqual(com.client_url_args[client_user_def456.id], {"user": "def456"})

        # 1. Send to all consumers
        com.broadcast(dumps({"event": "new_items", "_created": datetime.now().isoformat()}))
        broadcast_mock.assert_called_once_with(
            set(
                [
                    client_no_user,
                    client_user_abc123_sess_12345,
                    client_user_abc123_sess_67890,
                    client_user_def456,
                ]
            ),
            ANY,
        )
        broadcast_mock.reset_mock()

        # 2. Send to user: abc123
        com.broadcast(
            dumps(
                WebsocketMessageData(
                    event="new_items",
                    _created=datetime.now().isoformat(),
                    filters=dict(include={"user": ["abc123"]}),
                ),
            )
        )

        broadcast_mock.assert_called_once_with(
            set(
                [
                    client_user_abc123_sess_12345,
                    client_user_abc123_sess_67890,
                ]
            ),
            ANY,
        )

        broadcast_mock.reset_mock()

        # 3. Send to users: abc123 & def456
        com.broadcast(
            dumps(
                WebsocketMessageData(
                    event="new_items",
                    _created=datetime.now().isoformat(),
                    filters=dict(include={"user": ["abc123", "def456"]}),
                ),
            )
        )

        broadcast_mock.assert_called_once_with(
            set(
                [
                    client_user_abc123_sess_12345,
                    client_user_abc123_sess_67890,
                    client_user_def456,
                ]
            ),
            ANY,
        )

        broadcast_mock.reset_mock()

        # 4. Send to user: abc123, session: 67890
        com.broadcast(
            dumps(
                WebsocketMessageData(
                    event="new_items",
                    _created=datetime.now().isoformat(),
                    filters=dict(include={"user": ["abc123"], "session": ["67890"]}),
                ),
            )
        )

        broadcast_mock.assert_called_once_with(
            set(
                [
                    client_user_abc123_sess_67890,
                ]
            ),
            ANY,
        )

        broadcast_mock.reset_mock()

        # 5. Send to all consumers except user: abc123
        com.broadcast(
            dumps(
                WebsocketMessageData(
                    event="new_items",
                    _created=datetime.now().isoformat(),
                    filters=dict(exclude={"user": ["abc123"]}),
                ),
            )
        )

        broadcast_mock.assert_called_once_with(
            set(
                [
                    client_no_user,
                    client_user_def456,
                ]
            ),
            ANY,
        )

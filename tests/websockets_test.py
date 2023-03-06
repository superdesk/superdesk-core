from typing import List
import asyncio
import unittest
from json import dumps
from datetime import datetime, timedelta
from uuid import uuid4
from superdesk.websockets_comms import SocketCommunication
from superdesk.types import WebsocketMessageData


class TestClient:
    def __init__(self, path: str):
        self.open = True
        self.messages: List[str] = []
        self.path = path
        self.id = uuid4()

    def send(self, message):
        self.messages.append(message)


class WebsocketsTestCase(unittest.TestCase):
    def test_broadcast(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TestClient("")
        com = SocketCommunication("host", "port", "url")
        com.clients.add(client)

        loop.run_until_complete(
            com.broadcast(dumps({"event": "ingest:update", "_created": datetime.now().isoformat()}))
        )
        self.assertEqual(1, len(client.messages))

        loop.run_until_complete(
            com.broadcast(dumps({"event": "ingest:update", "_created": datetime.now().isoformat()}))
        )
        self.assertEqual(1, len(client.messages))

        loop.run_until_complete(com.broadcast(dumps({"event": "foo", "_created": datetime.now().isoformat()})))
        self.assertEqual(2, len(client.messages))

        loop.run_until_complete(com.broadcast(dumps({"event": "foo", "_created": datetime.now().isoformat()})))
        self.assertEqual(3, len(client.messages))

        loop.run_until_complete(
            com.broadcast(
                dumps({"event": "ingest:update", "_created": (datetime.now() + timedelta(seconds=3600)).isoformat()})
            )
        )
        self.assertEqual(4, len(client.messages))

    def test_broadcast_specific_recipients(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        com = SocketCommunication("host", "port", "url")

        client_no_user = TestClient("")
        client_user_abc123_sess_12345 = TestClient("/ws/subscribe?user=abc123&session=12345")
        client_user_abc123_sess_67890 = TestClient("/ws/subscribe?user=abc123&session=67890")
        client_user_def456 = TestClient("/ws/subscribe?user=def456")
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
        loop.run_until_complete(com.broadcast(dumps({"event": "new_items", "_created": datetime.now().isoformat()})))
        self.assertEqual(1, len(client_no_user.messages))
        self.assertEqual(1, len(client_user_abc123_sess_12345.messages))
        self.assertEqual(1, len(client_user_abc123_sess_67890.messages))
        self.assertEqual(1, len(client_user_def456.messages))

        # 2. Send to user: abc123
        loop.run_until_complete(
            com.broadcast(
                dumps(
                    WebsocketMessageData(
                        event="new_items",
                        _created=datetime.now().isoformat(),
                        filters=dict(include={"user": ["abc123"]}),
                    ),
                )
            )
        )
        self.assertEqual(1, len(client_no_user.messages))
        self.assertEqual(2, len(client_user_abc123_sess_12345.messages))
        self.assertEqual(2, len(client_user_abc123_sess_67890.messages))
        self.assertEqual(1, len(client_user_def456.messages))

        # 3. Send to users: abc123 & def456
        loop.run_until_complete(
            com.broadcast(
                dumps(
                    WebsocketMessageData(
                        event="new_items",
                        _created=datetime.now().isoformat(),
                        filters=dict(include={"user": ["abc123", "def456"]}),
                    ),
                )
            )
        )
        self.assertEqual(1, len(client_no_user.messages))
        self.assertEqual(3, len(client_user_abc123_sess_12345.messages))
        self.assertEqual(3, len(client_user_abc123_sess_67890.messages))
        self.assertEqual(2, len(client_user_def456.messages))

        # 4. Send to user: abc123, session: 67890
        loop.run_until_complete(
            com.broadcast(
                dumps(
                    WebsocketMessageData(
                        event="new_items",
                        _created=datetime.now().isoformat(),
                        filters=dict(include={"user": ["abc123"], "session": ["67890"]}),
                    ),
                )
            )
        )
        self.assertEqual(1, len(client_no_user.messages))
        self.assertEqual(3, len(client_user_abc123_sess_12345.messages))
        self.assertEqual(4, len(client_user_abc123_sess_67890.messages))
        self.assertEqual(2, len(client_user_def456.messages))

        # 5. Send to all consumers except user: abc123
        loop.run_until_complete(
            com.broadcast(
                dumps(
                    WebsocketMessageData(
                        event="new_items",
                        _created=datetime.now().isoformat(),
                        filters=dict(exclude={"user": ["abc123"]}),
                    ),
                )
            )
        )
        self.assertEqual(2, len(client_no_user.messages))
        self.assertEqual(3, len(client_user_abc123_sess_12345.messages))
        self.assertEqual(4, len(client_user_abc123_sess_67890.messages))
        self.assertEqual(3, len(client_user_def456.messages))

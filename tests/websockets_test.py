
import asyncio
import unittest
from json import dumps
from datetime import datetime, timedelta
from superdesk.websockets_comms import SocketCommunication


class TestClient():

    def __init__(self):
        self.open = True
        self.messages = []

    def send(self, message):
        self.messages.append(message)


class WebsocketsTestCase(unittest.TestCase):

    def test_broadcast(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TestClient()
        com = SocketCommunication('host', 'port', 'url')
        com.event_interval = {
            'foo': 5,
            'bar': 5,
        }
        com.clients.add(client)
        loop.run_until_complete(com.broadcast(dumps({'event': 'foo', '_created': datetime.now().isoformat()})))
        self.assertEqual(1, len(client.messages))
        loop.run_until_complete(com.broadcast(dumps({'event': 'foo', '_created': datetime.now().isoformat()})))
        self.assertEqual(1, len(client.messages))
        loop.run_until_complete(com.broadcast(dumps({'event': 'bar', '_created': datetime.now().isoformat()})))
        self.assertEqual(2, len(client.messages))
        loop.run_until_complete(com.broadcast(dumps({'event': 'baz', '_created': datetime.now().isoformat()})))
        loop.run_until_complete(com.broadcast(dumps({'event': 'baz', '_created': datetime.now().isoformat()})))
        self.assertEqual(4, len(client.messages))
        loop.run_until_complete(com.broadcast(dumps({
            'event': 'foo',
            '_created': (datetime.now() + timedelta(seconds=3600)).isoformat()
        })))
        self.assertEqual(5, len(client.messages))

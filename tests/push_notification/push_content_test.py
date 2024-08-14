from unittest import IsolatedAsyncioTestCase
import unittest.mock

from superdesk.flask import Flask
from apps.content import push_content_notification


class PushContentNotificationTestCase(IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = Flask(__name__)

    @unittest.mock.patch("apps.content.push_notification")
    async def test_push_content_notification(self, push_notification):
        async with self.app.app_context():
            foo1 = {"_id": "foo", "task": {"desk": "sports", "stage": "inbox"}}
            foo2 = {"_id": "foo", "task": {"desk": "news", "stage": "todo"}}
            foo3 = {"_id": "foo"}

            push_content_notification([foo1, foo2, foo3])
            push_notification.assert_called_once_with(
                "content:update",
                user="",
                items={"foo": 1},
                desks={"sports": 1, "news": 1},
                stages={"inbox": 1, "todo": 1},
            )

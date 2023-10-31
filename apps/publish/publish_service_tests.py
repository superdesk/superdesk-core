# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId
from nose.tools import assert_raises

from apps.publish import init_app
from superdesk.errors import PublishQueueError
from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.publish.publish_service import PublishService
from superdesk.tests import TestCase
import json
from werkzeug.datastructures import ImmutableMultiDict
from eve.utils import ParsedRequest
import superdesk


class PublishServiceTests(TestCase):
    queue_items = [
        {
            "_id": "571075791d41c81e204c5c8c",
            "destination": {"name": "NITF", "delivery_type": "ftp", "format": "nitf", "config": {}},
            "subscriber_id": "1",
            "state": "in-progress",
            "item_id": 1,
            "formatted_item": "",
        }
    ]

    subscribers = [
        {
            "_id": "1",
            "name": "Test",
            "subscriber_type": SUBSCRIBER_TYPES.WIRE,
            "media_type": "media",
            "is_active": True,
            "sequence_num_settings": {"max": 10, "min": 1},
            "critical_errors": {"9004": True},
            "destinations": [{"name": "NITF", "delivery_type": "ftp", "format": "nitf", "config": {}}],
        },
        {
            "_id": "2",
            "name": "Test2",
            "subscriber_type": SUBSCRIBER_TYPES.WIRE,
            "media_type": "media",
            "is_active": True,
            "sequence_num_settings": {"max": 10, "min": 1},
            "critical_errors": {"9004": True},
            "destinations": [
                {
                    "name": "HTTP PUSH",
                    "delivery_type": "http_push",
                    "format": "nitf",
                    "config": {
                        "resource_url": "http://localhost:5050/push",
                        "assets_url": "http://localhost:5050/push_binary",
                        "packaged": "true",
                        "secret_token": "newsroom",
                    },
                }
            ],
        },
        {
            "_id": "3",
            "name": "Test3",
            "subscriber_type": SUBSCRIBER_TYPES.WIRE,
            "media_type": "media",
            "is_active": True,
            "sequence_num_settings": {"max": 10, "min": 1},
            "critical_errors": {"9004": True},
            "destinations": [
                {
                    "name": "AMAZON SQS",
                    "delivery_type": "amazon_sqs_fifo",
                    "format": "nitf",
                    "config": {
                        "access_key_id": "demokeyaccess",
                        "attach_media": False,
                        "message_group_id": "messageGroupId",
                        "queue_name": "demo test",
                        "secret_access_key": "accesskey",
                    },
                }
            ],
        },
    ]

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert("subscribers", self.subscribers)
            self.queue_items[0]["_id"] = ObjectId(self.queue_items[0]["_id"])
            self.app.data.insert("publish_queue", self.queue_items)

            init_app(self.app)

    def test_close_subscriber_doesnt_close(self):
        with self.app.app_context():
            subscriber = self.app.data.find_one("subscribers", None)
            self.assertTrue(subscriber.get("is_active"))

            PublishService().close_transmitter(subscriber, PublishQueueError.unknown_format_error())
            subscriber = self.app.data.find_one("subscribers", None)
            self.assertTrue(subscriber.get("is_active"))

    def test_close_subscriber_does_close(self):
        with self.app.app_context():
            subscriber = self.app.data.find_one("subscribers", None)
            self.assertTrue(subscriber.get("is_active"))

            PublishService().close_transmitter(subscriber, PublishQueueError.bad_schedule_error())
            subscriber = self.app.data.find_one("subscribers", None)
            self.assertFalse(subscriber.get("is_active"))

    def test_transmit_closes_subscriber(self):
        def mock_transmit(*args):
            raise PublishQueueError.bad_schedule_error()

        with self.app.app_context():
            subscriber = self.app.data.find_one("subscribers", None)

            publish_service = PublishService()
            publish_service._transmit = mock_transmit

            with assert_raises(PublishQueueError):
                publish_service.transmit(self.queue_items[0])

            subscriber = self.app.data.find_one("subscribers", None)
            self.assertFalse(subscriber.get("is_active"))
            self.assertIsNotNone(subscriber.get("last_closed"))

    def test_highlight_query(self):
        source_query = {
            "query": {
                "filtered": {"query": {"query_string": {"query": "TEST", "lenient": True, "default_operator": "AND"}}}
            }
        }

        req = ParsedRequest()
        req.args = {"source": json.dumps(source_query)}
        req.args = ImmutableMultiDict(req.args)

        archive_service = superdesk.get_resource_service("published")
        req = archive_service._get_highlight_query(req)

        args = getattr(req, "args", {})
        source = json.loads(args.get("source")) if args.get("source") else {"query": {"filtered": {}}}

        self.assertEqual(len(source), 2)
        self.assertIn("query", source)
        self.assertIn("highlight", source)
        self.assertIn("fields", source["highlight"])
        self.assertEqual(
            ["body_html", "body_footer", "headline", "slugline", "abstract"], list(source["highlight"]["fields"].keys())
        )

    def test_subscribers_secret_token(self):
        subscriber_service = superdesk.get_resource_service("subscribers")
        data = list(subscriber_service.get(req=None, lookup={}))
        item = data[1]
        self.assertEqual("Test2", item["name"])
        self.assertNotIn("secret_token", item["destinations"][0]["config"])

        item = data[2]
        self.assertEqual("Test3", item["name"])
        self.assertNotIn("access_key_id", item["destinations"][0]["config"])
        self.assertNotIn("secret_access_key", item["destinations"][0]["config"])

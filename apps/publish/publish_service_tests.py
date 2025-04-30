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

from superdesk.core.resources import AsyncResourceService
from apps.publish import init_app
from superdesk.errors import PublishQueueError
from superdesk.types import SubscribersResource, PublishQueueResource
from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.publish.publish_service import PublishService
from superdesk.tests import TestCase
import json
from werkzeug.datastructures import ImmutableMultiDict
from eve.utils import ParsedRequest
import superdesk


SUBSCRIBER_IDS = [ObjectId(), ObjectId(), ObjectId()]


class PublishServiceTests(TestCase):
    subscriber_service: AsyncResourceService[SubscribersResource]
    queue_service: AsyncResourceService[PublishQueueResource]

    queue_items: list[PublishQueueResource] = [
        PublishQueueResource.from_dict(
            {
                "_id": ObjectId("571075791d41c81e204c5c8c"),
                "destination": {"name": "NITF", "delivery_type": "ftp", "format": "nitf", "config": {}},
                "subscriber_id": SUBSCRIBER_IDS[0],
                "state": "in-progress",
                "item_id": "1",
                "item_version": 1,
                "formatted_item": "",
                "publishing_action": "publish",
            }
        )
    ]

    subscribers: list[SubscribersResource] = [
        SubscribersResource.from_dict(
            {
                "_id": SUBSCRIBER_IDS[0],
                "name": "Test",
                "email": "foo@bar.org",
                "subscriber_type": SUBSCRIBER_TYPES.WIRE,
                "media_type": "media",
                "is_active": True,
                "sequence_num_settings": {"max": 10, "min": 1},
                "critical_errors": {"9004": True},
                "destinations": [{"name": "NITF", "delivery_type": "ftp", "format": "nitf", "config": {}}],
            }
        ),
        SubscribersResource.from_dict(
            {
                "_id": SUBSCRIBER_IDS[1],
                "name": "Test2",
                "email": "bar@foo.org",
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
            }
        ),
        SubscribersResource.from_dict(
            {
                "_id": SUBSCRIBER_IDS[2],
                "name": "Test3",
                "email": "foobar@orgs.org",
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
            }
        ),
    ]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.subscriber_service = SubscribersResource.get_service()
        self.queue_service = PublishQueueResource.get_service()

        await self.subscriber_service.create(self.subscribers)
        await self.queue_service.create(self.queue_items)

    async def test_close_subscriber_doesnt_close(self):
        subscriber = await self.subscriber_service.find_by_id(SUBSCRIBER_IDS[0])
        self.assertTrue(subscriber.is_active)

        await PublishService().close_transmitter(subscriber, PublishQueueError.unknown_format_error())
        subscriber = await self.subscriber_service.find_by_id(SUBSCRIBER_IDS[0])
        self.assertTrue(subscriber.is_active)

    async def test_close_subscriber_does_close(self):
        subscriber = await self.subscriber_service.find_by_id(SUBSCRIBER_IDS[0])
        self.assertTrue(subscriber.is_active)

        await PublishService().close_transmitter(subscriber, PublishQueueError.bad_schedule_error())
        subscriber = await self.subscriber_service.find_by_id(SUBSCRIBER_IDS[0])
        self.assertFalse(subscriber.is_active)

    async def test_transmit_closes_subscriber(self):
        def mock_transmit(*args):
            raise PublishQueueError.bad_schedule_error()

        publish_service = PublishService()
        publish_service._transmit = mock_transmit

        with self.assertRaises(PublishQueueError):
            await publish_service.transmit(self.queue_items[0].to_dict())

        subscriber = await self.subscriber_service.find_by_id(SUBSCRIBER_IDS[0])
        self.assertFalse(subscriber.is_active)
        self.assertIsNotNone(subscriber.last_closed)

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

    async def test_subscribers_secret_keys(self):
        subscribers = await self.subscriber_service.get_all_list()
        item = subscribers[1]
        self.assertEqual("Test2", item.name)
        self.assertNotIn("secret_token", item.destinations[0].config)

        item = subscribers[2]
        self.assertEqual("Test3", item.name)
        self.assertNotIn("access_key_id", item.destinations[0].config)
        self.assertNotIn("secret_access_key", item.destinations[0].config)

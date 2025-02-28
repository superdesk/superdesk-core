# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from unittest import mock
from datetime import timedelta
from bson import ObjectId

from superdesk.types import (
    PublishQueueResource,
    PublishQueueState,
    SubscribersResource,
    SubscriberDestination,
    SubscriberType,
)
from superdesk.resource_fields import ID_FIELD
from apps.publish import init_app
from apps.publish.enqueue import EnqueueContent
from superdesk.publish_async.publish_queue.utils import get_queue_items
from superdesk.tests import TestCase
from superdesk.utc import utcnow


class PublishContentTests(TestCase):
    subscriber = SubscribersResource(
        name="subscriberA",
        subscriber_type=SubscriberType.WIRE,
        email="subscriber@a.org",
    )
    queue_items: list[PublishQueueResource] = [
        PublishQueueResource(
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=subscriber.id,
            state=PublishQueueState.PENDING,
            item_id="1",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
        PublishQueueResource(
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=subscriber.id,
            state=PublishQueueState.PENDING,
            item_id="1",
            publish_schedule=utcnow() + timedelta(minutes=10),
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
        PublishQueueResource(
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=subscriber.id,
            state=PublishQueueState.PENDING,
            item_id="2",
            publish_schedule=utcnow() - timedelta(minutes=10),
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
        PublishQueueResource(
            destination=SubscriberDestination(
                delivery_type="content_api",
                format="ninjs",
                config={},
                name="destination1",
            ),
            subscriber_id=subscriber.id,
            state=PublishQueueState.SUCCESS,
            item_id="2",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
    ]

    published_items = [
        {
            "_id": 1,
            "item_id": "1",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "published",
        },
        {
            "_id": 2,
            "item_id": "2",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "scheduled",
            "publish_schedule": utcnow() - timedelta(minutes=5),
            "schedule_settings": {
                "utc_publish_schedule": utcnow() - timedelta(minutes=5),
                "timezone": "UTC",
                "utc_embargo": None,
            },
        },
        {
            "_id": 3,
            "item_id": "3",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "scheduled",
            "publish_schedule": utcnow() + timedelta(minutes=60),
            "schedule_settings": {
                "utc_publish_schedule": utcnow() + timedelta(minutes=60),
                "timezone": "UTC",
                "utc_embargo": None,
            },
        },
    ]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        init_app(self.app)

    async def test_queue_items(self):
        await SubscribersResource.get_service().create([self.subscriber])
        await PublishQueueResource.get_service().create(self.queue_items)

        items = await get_queue_items()
        self.assertEqual(3, await items.count())
        ids = [item.id async for item in items]
        self.assertNotIn(self.queue_items[3].id, ids)

    @mock.patch("apps.publish.enqueue.EnqueueContent.enqueue_item")
    def test_enqueue_item_not_scheduled(self, *mocks):
        fake_enqueue_item = mocks[0]
        queue_items = [{"_id": "1", "item_id": "item_1", "queue_state": "pending", "state": "published"}]
        EnqueueContent().enqueue_items(queue_items)
        fake_enqueue_item.assert_called_with(queue_items[0])

    async def test_get_enqueue_items(self):
        self.app.data.insert("published", self.published_items)
        items = EnqueueContent().get_published_items()
        self.assertEqual(2, len(items))
        ids = [item[ID_FIELD] for item in items]
        self.assertNotIn(3, ids)

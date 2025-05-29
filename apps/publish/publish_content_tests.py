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

from apps.publish import init_app
from apps.publish.enqueue import EnqueueContent
from superdesk import config, get_resource_service
from superdesk.publish.publish_content import get_queue_items
from superdesk.tests import TestCase
from superdesk.utc import utcnow


class PublishContentTests(TestCase):
    queue_items = [
        {
            "_id": 1,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "552ba73f1d41c8437971613e",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": 1,
        },
        {
            "_id": 2,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "552ba73f1d41c8437971613e",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": 1,
            "publish_schedule": utcnow() + timedelta(minutes=10),
        },
        {
            "_id": 3,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "552ba73f1d41c8437971613e",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "2",
            "publish_schedule": "2015-04-20T05:04:25.000Z",
        },
        {
            "_id": 4,
            "destination": {"delivery_type": "content_api", "format": "ninjs", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "552ba73f1d41c8437971613e",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "2",
        },
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

    def setUp(self):
        with self.app.app_context():
            init_app(self.app)

    def test_queue_items(self):
        with self.app.app_context():
            self.app.data.insert("publish_queue", self.queue_items)
            items = get_queue_items()
            self.assertEqual(3, items.count())
            ids = [item[config.ID_FIELD] for item in items]
            self.assertNotIn(4, ids)

    @mock.patch("apps.publish.enqueue.EnqueueContent.enqueue_item")
    def test_enqueue_item_not_scheduled(self, *mocks):
        fake_enqueue_item = mocks[0]
        queue_items = [{"_id": "1", "item_id": "item_1", "queue_state": "pending", "state": "published"}]
        EnqueueContent().enqueue_items(queue_items)
        fake_enqueue_item.assert_called_with(queue_items[0])

    def test_get_enqueue_items(self):
        self.app.data.insert("published", self.published_items)
        items = EnqueueContent().get_published_items()
        self.assertEqual(2, len(items))
        ids = [item[config.ID_FIELD] for item in items]
        self.assertNotIn(3, ids)

    def test_get_other_published_items(self):
        """Test that get_other_published_items returns all items with the same item_id."""
        with self.app.app_context():
            items = []

            # Insert multiple published items with the same item_id
            for i in range(20):
                items.append(
                    {
                        "_id": str(i + 1),
                        "item_id": "test_item",
                        "_created": utcnow(),
                        "_updated": utcnow(),
                        "queue_state": "pending",
                        "state": "published",
                    }
                )

            # add one item with a different item_id
            items.append(
                {
                    "_id": "21",
                    "item_id": "different_item",
                    "_created": utcnow(),
                    "_updated": utcnow(),
                    "queue_state": "pending",
                    "state": "published",
                }
            )

            self.app.data.insert("published", items)

            service = get_resource_service("published")
            result = service.get_other_published_items("test_item")

            # verify we got all items with item_id "test_item"
            result_list = list(result)
            self.assertEqual(20, len(result_list), "Should return all 20 items with the same item_id")

            # verify all expected IDs are present
            item_ids = [item["_id"] for item in result_list]
            for i in range(1, 21):
                self.assertIn(str(i), item_ids, f"Item with _id {i} should be in results")

            # verify the different item is not included
            self.assertNotIn("21", item_ids, "Item with different item_id should not be in results")

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
from unittest import mock
from unittest.mock import MagicMock
from datetime import timedelta
from collections import UserList

from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.publish.enqueue import enqueue_service
from superdesk.publish.publish_queue import PUBLISHED_IN_PACKAGE
from superdesk.publish import publish_queue
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE


class QueueItemsTestCase(TestCase):
    """Tests for the get_queue_items() function."""

    def setUp(self):
        try:
            from superdesk.publish.publish_content import get_queue_items
        except ImportError:
            self.fail("Could not import function under test (transmit_items).")
        else:
            self.func_under_test = get_queue_items
            self.queue_items = [
                {
                    "_id": ObjectId(),
                    "state": "pending",
                    "item_id": "item_1",
                    "item_version": 4,
                    "headline": "pending headline",
                    "destination": {},
                },
                {
                    "_id": ObjectId(),
                    "state": "retrying",
                    "item_id": "item_2",
                    "item_version": 4,
                    "headline": "retrying headline",
                    "retry_attempt": 2,
                    "next_retry_attempt_at": utcnow() + timedelta(minutes=30),
                },
                {
                    "_id": ObjectId(),
                    "state": "success",
                    "item_id": "item_3",
                    "item_version": 4,
                    "headline": "success headline",
                    "retry_attempt": 4,
                    "next_retry_attempt_at": utcnow() + timedelta(minutes=-30),
                },
                {
                    "_id": ObjectId(),
                    "state": "failed",
                    "item_id": "item_4",
                    "item_version": 4,
                    "headline": "failed headline",
                    "retry_attempt": 10,
                    "next_retry_attempt_at": utcnow() + timedelta(minutes=-30),
                },
                {
                    "_id": ObjectId(),
                    "state": "canceled",
                    "item_id": "item_5",
                    "item_version": 4,
                    "headline": "canceled headline",
                    "retry_attempt": 4,
                    "next_retry_attempt_at": utcnow() + timedelta(minutes=-30),
                },
                {
                    "_id": ObjectId(),
                    "state": "retrying",
                    "item_id": "item_6",
                    "item_version": 4,
                    "headline": "retrying headline",
                    "retry_attempt": 2,
                    "next_retry_attempt_at": utcnow() + timedelta(minutes=-30),
                },
            ]
            self.app.data.insert("publish_queue", self.queue_items)

    def test_get_queue_items(self):
        items = list(self.func_under_test())
        self.assertEqual(len(items), 1)
        for item in items:
            self.assertIn(item["item_id"], ["item_1"])

    def test_get_retry_queue_items(self):
        items = list(self.func_under_test(True))
        self.assertEqual(len(items), 1)
        for item in items:
            self.assertIn(item["item_id"], ["item_6"])

    def test_get_queue_items_with_retrying_items(self):
        item = self.app.data.find_one("publish_queue", req=None, _id=self.queue_items[1]["_id"])
        self.app.data.update(
            "publish_queue", item.get("_id"), {"next_retry_attempt_at": utcnow() - timedelta(minutes=30)}, item
        )
        items = list(self.func_under_test(True))
        self.assertEqual(len(items), 2)
        self.assertListEqual([item_l["item_id"] for item_l in items], ["item_2", "item_6"])

    @mock.patch.object(enqueue_service, "ObjectId")
    @mock.patch.object(enqueue_service, "get_utc_schedule")
    @mock.patch.object(enqueue_service, "get_resource_service")
    @mock.patch.object(enqueue_service, "get_formatter")
    def test_enqueue_dict(self, *mocks):
        get_formatter, get_resource_service, _, _ = mocks
        publish_queue = get_resource_service.return_value
        fake_post = publish_queue.post
        service = enqueue_service.EnqueueService()
        fake_formatter = get_formatter.return_value
        doc_dict = {ITEM_TYPE: CONTENT_TYPE.TEXT, PUBLISHED_IN_PACKAGE: False}
        fake_doc = MagicMock()
        fake_doc.__getitem__ = lambda s, k: doc_dict.get(k, MagicMock())
        fake_doc.get = doc_dict.get
        fake_destination = MagicMock()
        fake_subscriber = MagicMock()
        subs_dict = {"destinations": [fake_destination], "api_enabled": False}
        fake_subscriber.__getitem__ = lambda s, k: subs_dict.get(k, MagicMock())
        fake_subscriber["destinations"] = [fake_destination]
        subscribers = [fake_subscriber]
        fake_formatter.format.return_value = [{"published_seq_num": 42, "formatted_item": "test OK"}]
        service.get_destinations = MagicMock(return_value=fake_subscriber["destinations"])
        service.queue_transmission(fake_doc, subscribers)
        self.assertEqual(len(fake_post.call_args_list), 1)
        self.assertEqual(len(fake_post.call_args_list[0][0][0]), 1)
        doc = fake_post.call_args_list[0][0][0][0]
        self.assertEqual(doc["published_seq_num"], 42)
        self.assertEqual(doc["formatted_item"], "test OK")

        fake_post = publish_queue.post = MagicMock()
        fake_formatter.format.return_value = [{"this_should_not": "work", "bad_key": "value"}]
        service.queue_transmission(fake_doc, subscribers)
        # post should not have been called here,
        # because the dict is lacking the mandatory keys
        self.assertFalse(fake_post.called)

        fake_post = publish_queue.post = MagicMock()
        fake_formatter.format.return_value = [(42, "test tuple OK")]
        service.queue_transmission(fake_doc, subscribers)
        self.assertEqual(len(fake_post.call_args_list), 1)
        self.assertEqual(len(fake_post.call_args_list[0][0][0]), 1)
        doc = fake_post.call_args_list[0][0][0][0]
        self.assertEqual(doc["published_seq_num"], 42)
        self.assertEqual(doc["formatted_item"], "test tuple OK")

        fake_post = publish_queue.post = MagicMock()
        fake_formatter.format.return_value = [(1, "2", 3)]
        service.queue_transmission(fake_doc, subscribers)
        # post should not have been called here,
        # because the tuple should be in (published_seq_num, formatted_item) format
        self.assertFalse(fake_post.called)

    @mock.patch.object(publish_queue, "app")
    def test_delete_encoded_item(self, fake_app):
        fake_storage = fake_app.storage
        fake_storage_delete = fake_storage.delete
        service = publish_queue.PublishQueueService(backend=MagicMock())
        service.get_from_mongo = MagicMock()
        cursor = UserList([{"_id": "4567", "encoded_item_id": "TEST ID"}])
        cursor.sort = MagicMock()
        cursor.sort.return_value = cursor
        service.get_from_mongo.return_value = cursor
        service.delete({"_id": "4567"})
        assert fake_storage_delete.call_args == mock.call("TEST ID")

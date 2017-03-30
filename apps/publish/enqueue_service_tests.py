# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from .enqueue.enqueue_service import EnqueueService


class EnqueueServiceTest(TestCase):
    queue_items = [
        {
            "_id": 1,
            "destination": {
                "delivery_type": "ftp",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub1",
            "state": "pending",
            "associated_items": ["123"],
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '1',
            "item_version": 1,
            "publishing_action": "published"
        },
        {
            "_id": 2,
            "destination": {
                "delivery_type": "ftp",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub1",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '1',
            "item_version": 1,
            "publishing_action": "corrected",
            "associated_items": ["123"]
        },
        {
            "_id": 3,
            "destination": {
                "delivery_type": "ftp",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub2",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '2',
            "item_version": 1,
            "publishing_action": "published",
            "associated_items": ["123"]
        },
        {
            "_id": 4,
            "destination": {
                "delivery_type": "content_api",
                "format": "ninjs",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub2",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '2',
            "item_version": 2,
            "publishing_action": "corrected",
            "associated_items": ["456"]
        },
        {
            "_id": 5,
            "destination": {
                "delivery_type": "ftp",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub3",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '3',
            "item_version": 1,
            "publishing_action": "published",
            "associated_items": ["786"]
        },
        {
            "_id": 6,
            "destination": {
                "delivery_type": "content_api",
                "format": "ninjs",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub3",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '3',
            "item_version": 2,
            "publishing_action": "corrected"
        },
        {
            "_id": 7,
            "destination": {
                "delivery_type": "ftp",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub4",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '2',
            "item_version": 1,
            "publishing_action": "published",
            "associated_items": ["123"]
        },
        {
            "_id": 8,
            "destination": {
                "delivery_type": "content_api",
                "format": "ninjs",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub4",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '2',
            "item_version": 2,
            "publishing_action": "corrected",
            "associated_items": ["456"]
        },
        {
            "_id": 9,
            "destination": {
                "delivery_type": "content_api",
                "format": "ninjs",
                "config": {},
                "name": "destination1"
            },
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub5",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": '5',
            "item_version": 1,
            "publishing_action": "published"
        }
    ]

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert('publish_queue', self.queue_items)

    def test_previously_sent_item_association_for_one_subscriber(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = \
            service._get_subscribers_for_previously_sent_items({'item_id': '1'})
        self.assertEqual(len(associated_items.keys()), 1)
        self.assertIn('sub1', list(associated_items.keys()))
        self.assertIn('123', associated_items['sub1'])

    def test_previously_sent_item_association_for_multiple_subscribers(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = \
            service._get_subscribers_for_previously_sent_items({'item_id': '2'})
        self.assertEqual(len(associated_items.keys()), 2)
        self.assertIn('sub2', associated_items)
        self.assertIn('sub4', associated_items)
        self.assertIn('123', associated_items['sub2'])
        self.assertIn('456', associated_items['sub2'])
        self.assertIn('123', associated_items['sub4'])
        self.assertIn('456', associated_items['sub4'])

    def test_previously_sent_item_association_for_removed_associations(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = \
            service._get_subscribers_for_previously_sent_items({'item_id': '3'})
        self.assertEqual(len(associated_items.keys()), 1)
        self.assertIn('sub3', list(associated_items.keys()))
        self.assertIn('786', associated_items['sub3'])

    def test_previously_sent_item_association_for_no_associations(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = \
            service._get_subscribers_for_previously_sent_items({'item_id': '5'})
        self.assertEqual(len(associated_items.keys()), 0)

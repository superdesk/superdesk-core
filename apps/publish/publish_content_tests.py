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

from test_factory import SuperdeskTestCase
from superdesk.utc import utcnow
from datetime import timedelta
from superdesk.publish.publish_content import get_queue_items
from apps.publish import init_app
from superdesk import config
from apps.publish.enqueue import enqueue_items


class PublishContentTests(SuperdeskTestCase):
    queue_items = [{"_id": 1,
                    "destination": {
                        "delivery_type": "ftp",
                        "config": {},
                        "name": "destination1"
                    },
                    "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
                    "subscriber_id": "552ba73f1d41c8437971613e",
                    "state": "pending",
                    "_created": "2015-04-17T13:15:20.000Z",
                    "_updated": "2015-04-20T05:04:25.000Z",
                    "item_id": 1
                    },
                   {
                       "_id": 2,
                       "destination": {
                           "delivery_type": "ftp",
                           "config": {},
                           "name": "destination1"
                       },
                       "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
                       "subscriber_id": "552ba73f1d41c8437971613e",
                       "state": "pending",
                       "_created": "2015-04-17T13:15:20.000Z",
                       "_updated": "2015-04-20T05:04:25.000Z",
                       "item_id": 1,
                       "publish_schedule": utcnow() + timedelta(minutes=10)},
                   {
                       "_id": 3,
                       "destination": {
                           "delivery_type": "ftp",
                           "config": {},
                           "name": "destination1"
                       },
                       "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
                       "subscriber_id": "552ba73f1d41c8437971613e",
                       "state": "pending",
                       "_created": "2015-04-17T13:15:20.000Z",
                       "_updated": "2015-04-20T05:04:25.000Z",
                       "item_id": '2',
                       "publish_schedule": "2015-04-20T05:04:25.000Z"},
                   {
                       "_id": 4,
                       "destination": {
                           "delivery_type": "pull",
                           "config": {},
                           "name": "destination1"
                       },
                       "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
                       "subscriber_id": "552ba73f1d41c8437971613e",
                       "state": "pending",
                       "_created": "2015-04-17T13:15:20.000Z",
                       "_updated": "2015-04-20T05:04:25.000Z",
                       "item_id": '2'}]

    def setUp(self):
        super().setUp()
        with self.app.app_context():
            init_app(self.app)

    def test_queue_items(self):
        with self.app.app_context():
            self.app.data.insert('publish_queue', self.queue_items)
            items = get_queue_items()
            self.assertEqual(3, items.count())
            ids = [item[config.ID_FIELD] for item in items]
            self.assertNotIn(4, ids)

    @mock.patch('apps.publish.enqueue.enqueue_item')
    def test_enqueue_item_not_scheduled(self, *mocks):
        fake_enqueue_item = mocks[0]
        queue_items = [
            {'_id': '1', 'item_id': 'item_1', 'queue_state': 'pending',
             'state': 'published'}
        ]
        enqueue_items(queue_items)
        fake_enqueue_item.assert_called_with(queue_items[0])

    @mock.patch('apps.publish.enqueue.enqueue_item')
    def test_enqueue_item_scheduled_in_future(self, *mocks):
        fake_enqueue_item = mocks[0]
        queue_items = [
            {
                '_id': '1', 'item_id': 'item_1', 'queue_state': 'pending',
                'state': 'scheduled',
                'publish_schedule': utcnow() + timedelta(minutes=20),
                'schedule_settings': {
                    'utc_publish_schedule': utcnow() + timedelta(minutes=20),
                    'time_zone': None
                }
            }
        ]
        enqueue_items(queue_items)
        assert not fake_enqueue_item.called, 'method should not have been called'

    @mock.patch('apps.publish.enqueue.enqueue_item')
    def test_enqueue_item_scheduled_elapsed(self, *mocks):
        fake_enqueue_item = mocks[0]
        queue_items = [
            {
                '_id': '1', 'item_id': 'item_1', 'queue_state': 'pending',
                'state': 'scheduled',
                'publish_schedule': utcnow() + timedelta(minutes=-2),
                'schedule_settings': {
                    'utc_publish_schedule': utcnow() + timedelta(minutes=-2),
                    'time_zone': None
                }
            }
        ]
        enqueue_items(queue_items)
        fake_enqueue_item.assert_called_with(queue_items[0])

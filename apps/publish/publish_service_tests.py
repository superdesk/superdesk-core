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


class PublishServiceTests(TestCase):
    queue_items = [{"_id": "571075791d41c81e204c5c8c",
                    "destination": {"name": "NITF", "delivery_type": "ftp", "format": "nitf", "config": {}},
                    "subscriber_id": "1",
                    "state": "in-progress",
                    "item_id": 1,
                    "formatted_item": ''
                    }]

    subscribers = [{"_id": "1", "name": "Test", "subscriber_type": SUBSCRIBER_TYPES.WIRE, "media_type": "media",
                    "is_active": True, "sequence_num_settings": {"max": 10, "min": 1},
                    "critical_errors": {"9004": True},
                    "destinations": [{"name": "NITF", "delivery_type": "ftp", "format": "nitf", "config": {}}]
                    }]

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert('subscribers', self.subscribers)
            self.queue_items[0]['_id'] = ObjectId(self.queue_items[0]['_id'])
            self.app.data.insert('publish_queue', self.queue_items)

            init_app(self.app)

    def test_close_subscriber_doesnt_close(self):
        with self.app.app_context():
            subscriber = self.app.data.find_one('subscribers', None)
            self.assertTrue(subscriber.get('is_active'))

            PublishService().close_transmitter(subscriber, PublishQueueError.unknown_format_error())
            subscriber = self.app.data.find_one('subscribers', None)
            self.assertTrue(subscriber.get('is_active'))

    def test_close_subscriber_does_close(self):
        with self.app.app_context():
            subscriber = self.app.data.find_one('subscribers', None)
            self.assertTrue(subscriber.get('is_active'))

            PublishService().close_transmitter(subscriber, PublishQueueError.bad_schedule_error())
            subscriber = self.app.data.find_one('subscribers', None)
            self.assertFalse(subscriber.get('is_active'))

    def test_transmit_closes_subscriber(self):
        def mock_transmit(*args):
            raise PublishQueueError.bad_schedule_error()

        with self.app.app_context():
            subscriber = self.app.data.find_one('subscribers', None)

            publish_service = PublishService()
            publish_service._transmit = mock_transmit

            with assert_raises(PublishQueueError):
                publish_service.transmit(self.queue_items[0])

            subscriber = self.app.data.find_one('subscribers', None)
            self.assertFalse(subscriber.get('is_active'))
            self.assertIsNotNone(subscriber.get('last_closed'))

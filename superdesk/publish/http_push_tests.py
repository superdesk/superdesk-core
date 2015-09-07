# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import json
import os
import unittest

from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.publish.http_push import HTTPPushService, ItemNotFound
from time import sleep


class HTTPPushPublishTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()

        if 'HTTP_PUSH_RESOURCE_URL' not in os.environ or 'HTTP_PUSH_ITEM_URL' not in os.environ:
            return
        self.resource_url = os.environ['HTTP_PUSH_RESOURCE_URL']
        self.item_url = os.environ['HTTP_PUSH_ITEM_URL']

        self.subscribers = [{"_id": "1", "name": "Test", "media_type": "media",
                             "subscriber_type": SUBSCRIBER_TYPES.DIGITAL, "is_active": True,
                             "sequence_num_settings": {"max": 10, "min": 1},
                             "destinations": [{"name": "test", "delivery_type": "http_push", "format": "ninjs",
                                               "config": {"resource_url": self.resource_url, "item_url": self.item_url}
                                               }]}]
        self.item = {'item_id': 'item1',
                     'format': 'NITF',
                     'item_version': 1,
                     'published_seq_num': 1,
                     'formatted_item': '{"_id": "item1", "headline": "headline"}',
                     'destination': {"name": "test", "delivery_type": "http_push", "format": "ninjs",
                                     "config": {"resource_url": self.resource_url, "item_url": self.item_url}}
                     }

    def is_item_published(self, url, item_id):
        try:
            HTTPPushService()._get(url, item_id)
        except ItemNotFound:
            return False
        return True

    def test_publish_an_item(self):
        if not getattr(self, 'resource_url', None):
            return

        service = HTTPPushService()

        service._transmit(self.item, self.subscribers)
        self.assertTrue(self.is_item_published(self.item_url, self.item['item_id']))
        sleep(0.5)

        self.item['formatted_item'] = '{"_id": "item1", "headline": "headline2"}'
        service._transmit(self.item, self.subscribers)
        response = HTTPPushService()._get(self.item_url, self.item['item_id'])
        item = json.loads(response.read().decode(encoding='utf_8'))
        self.assertEqual(item['headline'], 'headline2')

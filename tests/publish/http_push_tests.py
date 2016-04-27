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
import requests

from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.publish.transmitters.http_push import HTTPPushService

from unittest import mock
from unittest.mock import Mock
from superdesk.errors import PublishHTTPPushError, PublishHTTPPushServerError, PublishHTTPPushClientError


class ItemNotFound(Exception):
    pass


class HTTPPushPublishTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()

        if 'HTTP_PUSH_RESOURCE_URL' not in os.environ:
            self.resource_url = ''
        else:
            self.resource_url = os.environ['HTTP_PUSH_RESOURCE_URL']

        self.subscribers = [{"_id": "1", "name": "Test", "media_type": "media",
                             "subscriber_type": SUBSCRIBER_TYPES.DIGITAL, "is_active": True,
                             "sequence_num_settings": {"max": 10, "min": 1},
                             "destinations": [{"name": "test", "delivery_type": "http_push", "format": "ninjs",
                                               "config": {"resource_url": self.resource_url}
                                               }]}]
        self.formatted_item1 = {"_id": "item1",
                                "headline": "headline",
                                "versioncreated": "2015-03-09T16:32:23",
                                "version": 1
                                }
        self.formatted_item2 = {"_id": "item1",
                                "headline": "headline2",
                                "versioncreated": "2015-03-21T13:43:51",
                                "version": 2
                                }
        self.item = {'item_id': 'item1',
                     'format': 'ninjs',
                     'item_version': 1,
                     'published_seq_num': 1,
                     'formatted_item': json.dumps(self.formatted_item1),
                     'destination': {"name": "test", "delivery_type": "http_push", "format": "ninjs",
                                     "config": {"resource_url": self.resource_url}
                                     }}

    def is_item_published(self, item_id):
        """Return True if the item was published, False otherwise.
        Raises Exception in case of server/communication error.
        """
        if not getattr(self, 'resource_url', None):
            return

        response = requests.get(self.getItemURL(item_id))
        if response.status_code == requests.codes.not_found:  # @UndefinedVariable
            return False
        self.assertEqual(response.status_code, requests.codes.ok,  # @UndefinedVariable
                         'Error retrieving item from the content API')
        return True

    def getItemURL(self, item_id):
        """Returns the URL for item read

        @param item_id: the item identifier
        @return: string
        """
        return '%s/%s' % (self.resource_url, item_id)

    def test_publish_an_item(self):
        if not getattr(self, 'resource_url', None):
            return

        service = HTTPPushService()

        service._transmit(self.item, self.subscribers)
        self.assertTrue(self.is_item_published(self.item['item_id']))

        self.item['formatted_item'] = json.dumps(self.formatted_item2)
        service._transmit(self.item, self.subscribers)
        item = requests.get(self.getItemURL(self.item['item_id'])).json()
        self.assertEqual(item['headline'], 'headline2')
        self.assertEqual(item['version'], 2)

    @mock.patch('superdesk.errors.notifiers')
    @mock.patch('requests.post')
    def test_client_publish_error_thrown(self, *mocks):
        fake_post = mocks[0]
        fake_post.return_value = Mock(status_code=401, text='client 4xx')

        # needed for bad exception handling classes
        fake_notifiers = mocks[1]
        fake_notifiers.return_value = []

        service = HTTPPushService()

        with self.assertRaises(PublishHTTPPushClientError):
            service._transmit(self.item, self.subscribers)

    @mock.patch('superdesk.errors.notifiers')
    @mock.patch('requests.post')
    def test_server_publish_error_thrown(self, *mocks):
        fake_post = mocks[0]
        fake_post.return_value = Mock(status_code=503, text='server 5xx')

        # needed for bad exception handling classes
        fake_notifiers = mocks[1]
        fake_notifiers.return_value = []

        service = HTTPPushService()

        with self.assertRaises(PublishHTTPPushServerError):
            service._transmit(self.item, self.subscribers)

    @mock.patch('superdesk.errors.notifiers')
    @mock.patch('requests.post')
    def test_publish_error_thrown(self, *mocks):
        fake_post = mocks[0]
        fake_post.return_value = Mock(status_code=600, text='error 6xx')

        # needed for bad exception handling classes
        fake_notifiers = mocks[1]
        fake_notifiers.return_value = []

        service = HTTPPushService()

        with self.assertRaises(PublishHTTPPushError):
            service._transmit(self.item, self.subscribers)

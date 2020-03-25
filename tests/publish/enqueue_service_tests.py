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

from superdesk.tests import TestCase
from content_api.publish.service import PublishService
from apps.publish.enqueue.enqueue_service import EnqueueService
from apps.packages.package_service import PackageService
from apps.archive.archive import ArchiveService


def _fake_extend_subscriber_items(self,
                                  subscriber_items,
                                  subscribers,
                                  package_item,
                                  package_item_id,
                                  subscriber_codes):
    subscriber_items.clear()
    subscriber_items.update({'8': {'subscriber': {
        '_id': 'toto',
        'is_targetable': True,
        'products': [],
        'api_products': ['570e04e23c5e9f89fe95366e'],
        'name': 'content_api',
        'subscriber_type': 'all',
        'destinations': [],
        'is_active': True,
        'sequence_num_settings': {'min': 1, 'max': 999},
        'api_enabled': True},
        'items': {'8': '8'},
        'codes': []}})


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
    content_api_package = {
        "_id": "10",
        "destination": {
            "delivery_type": "content_api",
            "format": "ninjs",
            "config": {},
            "name": "destination1"
        },
        "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
        "version": "2",
        "type": "composite",
        "headline": "test headline",
        "urgency": 3,
        "pubstatus": "usable",
        "slugline": "test slugline",
        "source": "foo",
        "associations": {"main-0": {"guid": "toto", "type": "text"},
                         "main-1": {"guid": "titi", "type": "text"}},
        "priority": 6,
        "subject": [{"code": "03003000", "name": "famine"}],
        "service": [{"code": "f", "name": "FIXME"}],
        "copyrightholder": "",
        "copyrightnotice": "",
        "usageterms": "",
        "state": "published",
        "genre": [{"name": "Article (news)", "code": "Article"}]}

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

    @mock.patch.object(PackageService, 'get_residrefs', lambda self, package: ['8', '9'])
    @mock.patch.object(ArchiveService, 'find_one', lambda self, req, **lookup: EnqueueServiceTest.content_api_package)
    @mock.patch.object(EnqueueService, '_extend_subscriber_items', _fake_extend_subscriber_items)
    @mock.patch.object(EnqueueService, 'queue_transmission', lambda *a, **kw: ([], True))
    @mock.patch.object(PublishService, 'publish')
    def test_content_api_package_publishing(self, content_api_publish):
        service = EnqueueService()
        service.enqueue_item(self.content_api_package)
        # Mock.assert_called_once is only available in Python 3.6
        # so we emulate it by counting the number of calls
        assert content_api_publish.call_count == 1

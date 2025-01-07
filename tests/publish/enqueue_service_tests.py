# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime, timedelta
from unittest import mock

from bson import ObjectId

from apps.archive.archive import ArchiveService
from apps.archive.common import ITEM_OPERATION
from apps.packages.package_service import PackageService
from apps.publish.enqueue import enqueue_service, PushContent
from apps.publish.enqueue import enqueue_published
from apps.publish.enqueue.enqueue_service import EnqueueService
from content_api.publish.service import PublishService
from superdesk import get_resource_service
from superdesk.errors import PublishQueueError
from superdesk.metadata.item import (
    CONTENT_STATE,
    ITEM_STATE,
    PUBLISH_SCHEDULE,
)
from superdesk.resource_fields import ID_FIELD, VERSION
from superdesk.tests import TestCase
from superdesk.utc import utcnow


def _fake_extend_subscriber_items(self, subscriber_items, subscribers, package_item, package_item_id, subscriber_codes):
    subscriber_items.clear()
    subscriber_items.update(
        {
            "8": {
                "subscriber": {
                    "_id": "toto",
                    "is_targetable": True,
                    "products": [],
                    "api_products": ["570e04e23c5e9f89fe95366e"],
                    "name": "content_api",
                    "subscriber_type": "all",
                    "destinations": [],
                    "is_active": True,
                    "sequence_num_settings": {"min": 1, "max": 999},
                    "api_enabled": True,
                },
                "items": {"8": "8"},
                "codes": [],
            }
        }
    )


class EnqueueServiceTest(TestCase):
    queue_items = [
        {
            "_id": 1,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub1",
            "state": "pending",
            "associated_items": ["123"],
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "1",
            "item_version": 1,
            "publishing_action": "published",
        },
        {
            "_id": 2,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub1",
            "state": "pending",
            "_created": "2015-04-17t13:15:20.000z",
            "_updated": "2015-04-20t05:04:25.000z",
            "item_id": "1",
            "item_version": 1,
            "publishing_action": "corrected",
            "associated_items": ["123"],
        },
        {
            "_id": 3,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub2",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "2",
            "item_version": 1,
            "publishing_action": "published",
            "associated_items": ["123"],
        },
        {
            "_id": 4,
            "destination": {"delivery_type": "content_api", "format": "ninjs", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub2",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "2",
            "item_version": 2,
            "publishing_action": "corrected",
            "associated_items": ["456"],
        },
        {
            "_id": 5,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub3",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "3",
            "item_version": 1,
            "publishing_action": "published",
            "associated_items": ["786"],
        },
        {
            "_id": 6,
            "destination": {"delivery_type": "content_api", "format": "ninjs", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub3",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "3",
            "item_version": 2,
            "publishing_action": "corrected",
        },
        {
            "_id": 7,
            "destination": {"delivery_type": "ftp", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub4",
            "state": "pending",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "2",
            "item_version": 1,
            "publishing_action": "published",
            "associated_items": ["123"],
        },
        {
            "_id": 8,
            "destination": {"delivery_type": "content_api", "format": "ninjs", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub4",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "2",
            "item_version": 2,
            "publishing_action": "corrected",
            "associated_items": ["456"],
        },
        {
            "_id": 9,
            "destination": {"delivery_type": "content_api", "format": "ninjs", "config": {}, "name": "destination1"},
            "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
            "subscriber_id": "sub5",
            "state": "success",
            "_created": "2015-04-17T13:15:20.000Z",
            "_updated": "2015-04-20T05:04:25.000Z",
            "item_id": "5",
            "item_version": 1,
            "publishing_action": "published",
        },
    ]
    content_api_package = {
        "_id": "10",
        "destination": {"delivery_type": "content_api", "format": "ninjs", "config": {}, "name": "destination1"},
        "_etag": "f28b9af64f169072fb171ec7f316fc03d5826d6b",
        "version": "2",
        "type": "composite",
        "headline": "test headline",
        "urgency": 3,
        "pubstatus": "usable",
        "slugline": "test slugline",
        "source": "foo",
        "associations": {"main-0": {"guid": "toto", "type": "text"}, "main-1": {"guid": "titi", "type": "text"}},
        "priority": 6,
        "subject": [{"code": "03003000", "name": "famine"}],
        "service": [{"code": "f", "name": "FIXME"}],
        "copyrightholder": "",
        "copyrightnotice": "",
        "usageterms": "",
        "state": "published",
        "genre": [{"name": "Article (news)", "code": "Article"}],
    }

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.data.insert("publish_queue", self.queue_items)

    async def test_previously_sent_item_association_for_one_subscriber(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = service._get_subscribers_for_previously_sent_items(
            {"item_id": "1"}
        )
        self.assertEqual(len(associated_items.keys()), 1)
        self.assertIn("sub1", list(associated_items.keys()))
        self.assertIn("123", associated_items["sub1"])

    async def test_previously_sent_item_association_for_multiple_subscribers(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = service._get_subscribers_for_previously_sent_items(
            {"item_id": "2"}
        )
        self.assertEqual(len(associated_items.keys()), 2)
        self.assertIn("sub2", associated_items)
        self.assertIn("sub4", associated_items)
        self.assertIn("123", associated_items["sub2"])
        self.assertIn("456", associated_items["sub2"])
        self.assertIn("123", associated_items["sub4"])
        self.assertIn("456", associated_items["sub4"])

    async def test_previously_sent_item_association_for_removed_associations(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = service._get_subscribers_for_previously_sent_items(
            {"item_id": "3"}
        )
        self.assertEqual(len(associated_items.keys()), 1)
        self.assertIn("sub3", list(associated_items.keys()))
        self.assertIn("786", associated_items["sub3"])

    async def test_previously_sent_item_association_for_no_associations(self):
        service = EnqueueService()
        subscribers, subscriber_codes, associated_items = service._get_subscribers_for_previously_sent_items(
            {"item_id": "5"}
        )
        self.assertEqual(len(associated_items.keys()), 0)

    @mock.patch.object(PackageService, "get_residrefs", lambda self, package: ["8", "9"])
    @mock.patch.object(ArchiveService, "find_one", lambda self, req, **lookup: EnqueueServiceTest.content_api_package)
    @mock.patch.object(EnqueueService, "_extend_subscriber_items", _fake_extend_subscriber_items)
    @mock.patch.object(EnqueueService, "queue_transmission", lambda *a, **kw: ([], True))
    @mock.patch.object(PublishService, "publish")
    async def test_content_api_package_publishing(self, content_api_publish):
        service = EnqueueService()
        service.enqueue_item(self.content_api_package)
        # Mock.assert_called_once is only available in Python 3.6
        # so we emulate it by counting the number of calls
        assert content_api_publish.call_count == 1

    async def test_queue_transmission_with_cache(self):
        service = EnqueueService()
        doc = {
            ID_FIELD: "test_id",
            "type": "text",
            VERSION: 1,
            "item_id": "test_id",
            "unique_name": "test_unique_name",
            "headline": "test_headline",
            "priority": 1,
        }
        subscribers = [
            {"_id": "sub1", "name": "Subscriber 1", "priority": 1},
            {"_id": "sub2", "name": "Subscriber 2", "priority": 2},
        ]

        formatter = mock.Mock()
        formatter.use_cache = True
        formatter.format.return_value = [
            {
                "published_seq_num": 1,
                "formatted_item": "formatted_content",
            }
        ]

        with mock.patch.object(enqueue_service, "get_formatter", return_value=formatter):
            with mock.patch.object(
                EnqueueService, "get_destinations", return_value=[{"format": "ninjs", "delivery_type": "ftp"}]
            ):
                # There should be only the first call, to format the document
                service.queue_transmission(doc, subscribers)
                formatter.format.assert_called_once()

    async def test_queue_transmission_without_cache(self):
        service = EnqueueService()
        doc = {
            ID_FIELD: "test_id",
            "type": "text",
            VERSION: 1,
            "item_id": "test_id",
            "unique_name": "test_unique_name",
            "headline": "test_headline",
            "priority": 1,
        }
        subscribers = [
            {"_id": "sub1", "name": "Subscriber 1", "priority": 1},
            {"_id": "sub2", "name": "Subscriber 2", "priority": 2},
        ]

        formatter = mock.Mock()
        formatter.use_cache = False
        formatter.format.return_value = [
            {
                "published_seq_num": 1,
                "formatted_item": "formatted_content",
            }
        ]

        with mock.patch.object(enqueue_service, "get_formatter", return_value=formatter):
            with mock.patch.object(
                EnqueueService, "get_destinations", return_value=[{"format": "ninjs", "delivery_type": "ftp"}]
            ):
                service.queue_transmission(doc, subscribers)
                self.assertEqual(formatter.format.call_count, 2)


class PushContentTest(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.test_id_1 = ObjectId()
        self.test_id_2 = ObjectId()
        self.test_id_3 = ObjectId()
        items = [
            {
                "_id": self.test_id_1,
                "item_id": self.test_id_1,
                "type": "text",
                "headline": "test headline toto",
                "version": 1,
                "task": {},
                ITEM_STATE: CONTENT_STATE.SCHEDULED,
                ITEM_OPERATION: "publish",
                PUBLISH_SCHEDULE: utcnow() + timedelta(hours=1),
            },
            {
                "_id": self.test_id_2,
                "item_id": "2",
                "type": "text",
                "headline": "test headline 2",
                "version": 1,
                "task": {},
                ITEM_STATE: CONTENT_STATE.SCHEDULED,
                ITEM_OPERATION: "publish",
                PUBLISH_SCHEDULE: utcnow() - timedelta(hours=1),
            },
            {
                "_id": self.test_id_3,
                "item_id": "3",
                "type": "text",
                "headline": "test headline 3",
                VERSION: 1,
                "task": {},
                ITEM_STATE: CONTENT_STATE.PUBLISHED,
                ITEM_OPERATION: "publish",
            },
        ]

        self.app.data.insert("archive", items)
        self.app.data.insert("published", items)

    @mock.patch.object(EnqueueService, "enqueue_item")
    async def test_push_scheduled_item_in_future(self, mock_enqueue):
        """``enqueue_item`` is not called if the item is scheduled in the future."""
        with mock.patch.object(get_resource_service("published"), "patch") as mock_patch:
            mock_patch.return_value = None
            cmd = PushContent()
            cmd.run(str(self.test_id_1))
            mock_enqueue.assert_not_called()

    @mock.patch.object(EnqueueService, "enqueue_item")
    async def test_push_scheduled_item_in_past(self, mock_enqueue):
        """``enqueue_item`` is called if the item is scheduled but the publish schedule is passed."""
        with mock.patch.object(get_resource_service("published"), "patch") as mock_patch:
            mock_patch.return_value = None
            cmd = PushContent()
            cmd.run(str(self.test_id_2))
            mock_enqueue.assert_called_once()

    @mock.patch("apps.publish.enqueue.enqueue_service.get_resource_service", return_value=None)
    async def test_push_non_existent_item(self, mock_get_resource_service):
        """Exception is raise if item is not found."""
        with mock.patch.object(get_resource_service("published"), "patch") as mock_patch:
            mock_patch.return_value = None
            cmd = PushContent()
            non_existent_id = ObjectId()
            with self.assertRaises(PublishQueueError):
                cmd.run(str(non_existent_id))

    @mock.patch.object(EnqueueService, "enqueue_item")
    async def test_push_with_content_type(self, mock_enqueue):
        """Content type is used when present."""
        with mock.patch.object(get_resource_service("published"), "patch") as mock_patch:
            mock_patch.return_value = None
            cmd = PushContent()
            cmd.run(str(self.test_id_2), "test_content_type")
            mock_enqueue.assert_called_once_with(mock.ANY, "test_content_type")

    @mock.patch.object(EnqueueService, "enqueue_item")
    async def test_push_publish(self, mock_enqueue):
        """Push publish calls ``enqueue_item`` when it's not scheduled."""
        with mock.patch.object(get_resource_service("published"), "patch") as mock_patch:
            mock_patch.return_value = None
            cmd = PushContent()
            cmd.run(str(self.test_id_3))
            mock_enqueue.assert_called_once()

    @mock.patch.object(EnqueueService, "enqueue_item", side_effect=Exception("Test error"))
    async def test_push_with_enqueue_error(self, mock_enqueue):
        """Exception is propagated when ``enqueue_item`` raises one."""
        with mock.patch.object(get_resource_service("published"), "patch") as mock_patch:
            mock_patch.return_value = None
            cmd = PushContent()
            with self.assertRaises(Exception) as context:
                cmd.run(str(self.test_id_2))
            assert str(context.exception) == "Test error"

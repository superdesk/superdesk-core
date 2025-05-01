# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId
from superdesk.tests import TestCase, utils as test_utils, fixtures


class ExpiredArchiveContentTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        try:
            from apps.archive.commands import RemoveExpiredContent
        except ImportError:
            self.fail("Could not import class under test (RemoveExpiredContent).")
        else:
            self.class_under_test = RemoveExpiredContent
            self.published_items = [
                {
                    "_id": "item1",
                    "item_id": "item1",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "_current_version": 3,
                    "moved_to_legal": True,
                    "state": "published",
                },
                {
                    "_id": "item2",
                    "item_id": "item2",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "_current_version": 3,
                    "moved_to_legal": True,
                    "state": "published",
                },
                {
                    "_id": "item3",
                    "item_id": "item3",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "_current_version": 3,
                    "moved_to_legal": False,
                    "state": "published",
                },
                {
                    "_id": "item4",
                    "item_id": "item4",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "_current_version": 3,
                    "moved_to_legal": True,
                    "state": "published",
                },
            ]

            self.queue_items = [
                {
                    # "_id": "item1",
                    "item_id": "item1",
                    "headline": "headline",
                    "item_version": 3,
                    "moved_to_legal": True,
                    "publishing_action": "publish",
                    "formatted_item": "",
                    "subscriber_id": fixtures.subscribers.SUB5_ID,
                },
                {
                    # "_id": "item2",
                    "item_id": "item2",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": True,
                    "publishing_action": "publish",
                    "formatted_item": "",
                    "subscriber_id": fixtures.subscribers.SUB5_ID,
                },
                {
                    # "_id": "item3",
                    "item_id": "item3",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": False,
                    "publishing_action": "publish",
                    "formatted_item": "",
                    "subscriber_id": fixtures.subscribers.SUB5_ID,
                },
                {
                    # "_id": "item4",
                    "item_id": "item4",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": False,
                    "publishing_action": "publish",
                    "formatted_item": "",
                    "subscriber_id": fixtures.subscribers.SUB5_ID,
                },
                {
                    # "_id": "item5",
                    "item_id": "item4",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": True,
                    "publishing_action": "publish",
                    "formatted_item": "",
                    "subscriber_id": fixtures.subscribers.SUB5_ID,
                },
            ]

            await test_utils.post_items("products", fixtures.products.all_products())
            await test_utils.post_items("subscribers", fixtures.subscribers.all_subscribers())
            await test_utils.post_items("published", self.published_items)
            await test_utils.post_items("publish_queue", self.queue_items)

    async def test_items_moved_to_legal_success(self):
        self.maxDiff = None
        test_items = dict()
        test_items["item1"] = self.published_items[0]
        test_items["item2"] = self.published_items[1]
        result = await self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertDictEqual(result, {})

    async def test_items_moved_to_legal_fail_if_published_item_not_moved(self):
        test_items = dict()
        test_items["item2"] = self.published_items[1]
        test_items["item3"] = self.published_items[2]
        result = await self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertIn("item3", result)

    async def test_items_moved_to_legal_fail_if_published_queue_item_not_moved(self):
        test_items = dict()
        test_items["item2"] = self.published_items[1]
        test_items["item3"] = self.published_items[3]
        result = await self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertIn("item3", result)

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


class ExpiredArchiveContentTestCase(TestCase):
    def setUp(self):
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
                },
                {
                    "_id": "item2",
                    "item_id": "item2",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "_current_version": 3,
                    "moved_to_legal": True,
                },
                {
                    "_id": "item3",
                    "item_id": "item3",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "_current_version": 3,
                    "moved_to_legal": False,
                },
                {
                    "_id": "item4",
                    "item_id": "item4",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "_current_version": 3,
                    "moved_to_legal": True,
                },
            ]

            self.queue_items = [
                {"_id": "item1", "item_id": "item1", "headline": "headline", "item_version": 3, "moved_to_legal": True},
                {
                    "_id": "item2",
                    "item_id": "item2",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": True,
                },
                {
                    "_id": "item3",
                    "item_id": "item3",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": False,
                },
                {
                    "_id": "item4",
                    "item_id": "item4",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": False,
                },
                {
                    "_id": "item5",
                    "item_id": "item4",
                    "headline": "headline",
                    "source": "aap",
                    "body_html": "test",
                    "item_version": 3,
                    "moved_to_legal": True,
                },
            ]

            self.app.data.insert("published", self.published_items)
            self.app.data.insert("publish_queue", self.queue_items)

    def test_items_moved_to_legal_success(self):
        test_items = dict()
        test_items["item1"] = self.published_items[0]
        test_items["item2"] = self.published_items[1]
        result = self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertDictEqual(result, {})

    def test_items_moved_to_legal_fail_if_published_item_not_moved(self):
        test_items = dict()
        test_items["item2"] = self.published_items[1]
        test_items["item3"] = self.published_items[2]
        result = self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertIn("item3", result)

    def test_items_moved_to_legal_fail_if_published_queue_item_not_moved(self):
        test_items = dict()
        test_items["item2"] = self.published_items[1]
        test_items["item3"] = self.published_items[3]
        result = self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertIn("item3", result)

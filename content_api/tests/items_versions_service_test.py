# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016, 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.tests import TestCase
from superdesk import get_resource_service


class ItemDeleteTestCase(TestCase):
    """Tests that item_version documents are deleted when the items document is deleted"""

    def setUp(self):
        self.app.data.insert(
            "items",
            [
                {"_id": "item1", "type": "text"},
                {"_id": "item2", "type": "text"},
                {"_id": "item3", "type": "text"},
                {"_id": "item4", "type": "text"},
                {"_id": "item5", "type": "text"},
            ],
        )
        self.app.data.insert(
            "items_versions",
            [
                {"_id": "ver1", "type": "text", "_id_document": "item1"},
                {"_id": "ver2", "type": "text", "_id_document": "item2"},
                {"_id": "ver3", "type": "text", "_id_document": "item3"},
                {"_id": "ver4", "type": "text", "_id_document": "item4"},
                {"_id": "ver5", "type": "text", "_id_document": "item5"},
            ],
        )

    def test_event_fired(self):
        items_service = get_resource_service("items")
        items_versions_service = get_resource_service("items_versions")

        item_ids = ["item1", "item2", "item3", "item4", "item5"]
        ver_ids = ["ver1", "ver2", "ver3", "ver4", "ver5"]

        items_service.delete_action(lookup={"_id": {"$in": item_ids}})
        for item_id in item_ids:
            item = items_service.find_one(req=None, _id=item_id)
            self.assertIsNone(item)

        for ver_id in ver_ids:
            item_version = items_versions_service.find_one(req=None, _id=ver_id)
            self.assertIsNone(item_version)

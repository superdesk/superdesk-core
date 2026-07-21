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

from superdesk import get_resource_service
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.archived.commands import UnarchiveItemCommand


class UnarchiveItemCommandTestCase(TestCase):
    def _post_archived(self, item_id):
        get_resource_service("archived").post(
            [
                {
                    "_id": ObjectId(),
                    "item_id": item_id,
                    "guid": item_id,
                    "_current_version": 1,
                    "versioncreated": utcnow(),
                    "type": "text",
                    "state": "published",
                }
            ]
        )

    def _count(self, resource, lookup):
        return len(list(get_resource_service(resource).get_from_mongo(req=None, lookup=lookup)))

    def test_unarchive_single_item(self):
        self._post_archived("test")

        UnarchiveItemCommand().run(["test"])

        self.assertEqual(self._count("archived", {"item_id": "test"}), 0)
        self.assertEqual(self._count("archive", {"_id": "test"}), 1)
        self.assertEqual(self._count("published", {"item_id": "test"}), 1)

    def test_unarchive_defaults_expiry_to_null(self):
        self._post_archived("null-expiry")

        UnarchiveItemCommand().run(["null-expiry"])

        archive_doc = get_resource_service("archive").find_one(req=None, _id="null-expiry")
        self.assertIsNotNone(archive_doc)
        self.assertIsNone(archive_doc.get("expiry"))

    def test_unarchive_expiry_days_override_sets_expiry(self):
        self._post_archived("override-expiry")

        UnarchiveItemCommand().run(["override-expiry"], expiry_days=30)

        archive_doc = get_resource_service("archive").find_one(req=None, _id="override-expiry")
        self.assertIsNotNone(archive_doc)
        self.assertIsNotNone(archive_doc.get("expiry"))

    def test_unarchive_no_ids_is_noop(self):
        results = UnarchiveItemCommand().run([])

        self.assertEqual(results, {"success": [], "failed": []})

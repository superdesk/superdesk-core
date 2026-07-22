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

from bson import ObjectId

from superdesk import get_resource_service
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.archived.commands import UnarchiveItemCommand


class UnarchiveItemCommandTestCase(TestCase):
    def _post_archived(self, item_id, **extra):
        doc = {
            "_id": ObjectId(),
            "item_id": item_id,
            "guid": item_id,
            "_current_version": 1,
            "versioncreated": utcnow(),
            "type": "text",
            "state": "published",
        }
        doc.update(extra)
        get_resource_service("archived").post([doc])

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

    def test_unarchive_negative_expiry_days_is_rejected(self):
        with self.assertRaises(ValueError):
            UnarchiveItemCommand().run(["whatever"], expiry_days=-1)

    def test_unarchive_no_ids_is_noop(self):
        results = UnarchiveItemCommand().run([])

        self.assertEqual(results, {"success": [], "failed": []})

    def test_unarchive_composite_restores_members_before_package(self):
        self._post_archived("member-1")
        self._post_archived(
            "composite-1",
            type="composite",
            groups=[
                {"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"residRef": "member-1", "location": "archived"}]},
            ],
        )

        order = []
        original_restore_to_archive = UnarchiveItemCommand._restore_to_archive

        def spy(self, item, expiry_days):
            order.append(item["item_id"])
            return original_restore_to_archive(self, item, expiry_days)

        with mock.patch.object(UnarchiveItemCommand, "_restore_to_archive", spy):
            UnarchiveItemCommand().run(["composite-1"])

        # members must be restored before the package that references them
        self.assertEqual(order, ["member-1", "composite-1"])

        for item_id in ["member-1", "composite-1"]:
            self.assertEqual(self._count("archived", {"item_id": item_id}), 0)
            self.assertEqual(self._count("archive", {"_id": item_id}), 1)

    def test_unarchive_takes_package_restores_all_takes(self):
        self._post_archived("take-1", linked_in_packages=[{"package": "takes-pkg", "package_type": "takes"}])
        self._post_archived("take-2")
        self._post_archived(
            "takes-pkg",
            type="composite",
            groups=[{"id": "main", "refs": [{"residRef": "take-1"}, {"residRef": "take-2"}]}],
        )

        # unarchiving one take pulls in the whole takes package
        UnarchiveItemCommand().run(["take-1"])

        for item_id in ["take-1", "take-2", "takes-pkg"]:
            self.assertEqual(self._count("archived", {"item_id": item_id}), 0)
            self.assertEqual(self._count("archive", {"_id": item_id}), 1)

    def test_unarchive_dry_run_makes_no_changes(self):
        self._post_archived("dry-1")

        UnarchiveItemCommand().run(["dry-1"], dry_run=True)

        self.assertEqual(self._count("archived", {"item_id": "dry-1"}), 1)
        self.assertEqual(self._count("archive", {"_id": "dry-1"}), 0)
        self.assertEqual(self._count("published", {"item_id": "dry-1"}), 0)

    def test_unarchive_rolls_back_on_partial_failure(self):
        self._post_archived("rollback-member")
        self._post_archived(
            "rollback-pkg",
            type="composite",
            groups=[
                {"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"residRef": "rollback-member", "location": "archived"}]},
            ],
        )

        original_restore_to_published = UnarchiveItemCommand._restore_to_published

        def flaky(self, item):
            if item["item_id"] == "rollback-pkg":
                raise RuntimeError("boom")
            return original_restore_to_published(self, item)

        with mock.patch.object(UnarchiveItemCommand, "_restore_to_published", flaky):
            results = UnarchiveItemCommand().run(["rollback-pkg"])

        self.assertEqual(results["success"], [])
        self.assertEqual(len(results["failed"]), 1)

        # nothing left half-restored in archive or published
        for item_id in ["rollback-member", "rollback-pkg"]:
            self.assertEqual(self._count("archive", {"_id": item_id}), 0)
            self.assertEqual(self._count("published", {"item_id": item_id}), 0)
            # archived is only cleaned up after a fully successful restore
            self.assertEqual(self._count("archived", {"item_id": item_id}), 1)

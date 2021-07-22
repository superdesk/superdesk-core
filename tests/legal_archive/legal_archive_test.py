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

from unittest.mock import MagicMock
from datetime import timedelta

from eve.versioning import resolve_document_version
from eve.utils import ParsedRequest

from apps.archive.common import insert_into_versions, ARCHIVE
from superdesk import get_resource_service
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.legal_archive.commands import LegalArchiveImport


class LegalArchiveTestCase(TestCase):

    desks = [{"_id": "123", "name": "Sports"}]
    users = [{"_id": "123", "username": "test1", "first_name": "test", "last_name": "user", "email": "a@a.com"}]
    stages = [{"_id": "123", "name": "working stage", "desk": "123"}]
    archive = [
        {"task": {"desk": "123", "stage": "123"}},
        {"task": {"desk": "1234", "stage": None, "user": "123"}},
        {"task": {"desk": "1234", "stage": "dddd", "user": "test"}},
    ]

    def setUp(self):
        self.app.data.insert("desks", self.desks)
        self.app.data.insert("users", self.users)
        self.app.data.insert("stages", self.stages)

    def test_denormalize_desk_user(self):
        LegalArchiveImport()._denormalize_user_desk(self.archive[0], "")
        task = self.archive[0]["task"]
        self.assertEqual(task.get("desk"), "Sports")
        self.assertEqual(task.get("stage"), "working stage")
        self.assertEqual(task.get("user"), "")

    def test_denormalize_not_configured_desk(self):
        LegalArchiveImport()._denormalize_user_desk(self.archive[1], "")
        task = self.archive[1]["task"]
        self.assertEqual(task.get("desk"), "1234")
        self.assertEqual(task.get("stage"), None)
        self.assertEqual(task.get("user"), "test user")

    def test_denormalize_not_configured_desk_stage_user(self):
        LegalArchiveImport()._denormalize_user_desk(self.archive[2], "")
        task = self.archive[2]["task"]
        self.assertEqual(task.get("desk"), "1234")
        self.assertEqual(task.get("stage"), "dddd")
        self.assertEqual(task.get("user"), "")


class ImportLegalArchiveCommandTestCase(TestCase):
    desks = [{"name": "Sports"}]
    users = [{"username": "test1", "first_name": "test", "last_name": "user", "email": "a@a.com"}]

    def setUp(self):
        try:
            from apps.legal_archive.commands import ImportLegalArchiveCommand
        except ImportError:
            self.fail("Could not import class under test (ImportLegalArchiveCommand).")
        else:
            self.class_under_test = ImportLegalArchiveCommand
            self.app.data.insert("desks", self.desks)
            self.app.data.insert("users", self.users)
            self.validators = [
                {"schema": {}, "type": "text", "act": "publish", "_id": "publish_text"},
                {"schema": {}, "type": "text", "act": "correct", "_id": "correct_text"},
                {"schema": {}, "type": "text", "act": "kill", "_id": "kill_text"},
            ]

            self.products = [
                {"_id": "1", "name": "prod1"},
                {"_id": "2", "name": "prod2", "codes": "abc,def"},
                {"_id": "3", "name": "prod3", "codes": "xyz"},
            ]

            self.subscribers = [
                {
                    "name": "Test",
                    "is_active": True,
                    "subscriber_type": "wire",
                    "email": "test@test.com",
                    "sequence_num_settings": {"max": 9999, "min": 1},
                    "products": ["1"],
                    "destinations": [
                        {
                            "name": "test",
                            "delivery_type": "email",
                            "format": "nitf",
                            "config": {"recipients": "test@test.com"},
                        }
                    ],
                }
            ]
            self.app.data.insert("validators", self.validators)
            self.app.data.insert("products", self.products)
            self.app.data.insert("subscribers", self.subscribers)
            self.class_under_test = ImportLegalArchiveCommand
            self.archive_items = [
                {
                    "task": {"desk": self.desks[0]["_id"], "stage": self.desks[0]["incoming_stage"], "user": "123"},
                    "_id": "item1",
                    "state": "in_progress",
                    "headline": "item 1",
                    "type": "text",
                    "slugline": "item 1 slugline",
                    "_current_version": 1,
                    "_created": utcnow() - timedelta(minutes=3),
                    "expired": utcnow() - timedelta(minutes=30),
                },
                {
                    "task": {"desk": self.desks[0]["_id"], "stage": self.desks[0]["incoming_stage"], "user": "123"},
                    "_id": "item2",
                    "state": "in_progress",
                    "headline": "item 2",
                    "type": "text",
                    "slugline": "item 2 slugline",
                    "_current_version": 1,
                    "_created": utcnow() - timedelta(minutes=2),
                    "expired": utcnow() - timedelta(minutes=30),
                },
                {
                    "task": {"desk": self.desks[0]["_id"], "stage": self.desks[0]["incoming_stage"], "user": "123"},
                    "_id": "item3",
                    "state": "in_progress",
                    "headline": "item 2",
                    "type": "text",
                    "slugline": "item 2 slugline",
                    "_current_version": 1,
                    "_created": utcnow() - timedelta(minutes=1),
                    "expired": utcnow() - timedelta(minutes=30),
                },
            ]

            get_resource_service(ARCHIVE).post(self.archive_items)
            for item in self.archive_items:
                resolve_document_version(item, ARCHIVE, "POST")
                insert_into_versions(id_=item["_id"])

    def test_import_into_legal_archive(self):
        archive_publish = get_resource_service("archive_publish")
        archive_correct = get_resource_service("archive_correct")
        legal_archive = get_resource_service("legal_archive")
        archive = get_resource_service("archive_publish")
        published = get_resource_service("published")
        publish_queue = get_resource_service("publish_queue")

        self.original_method = LegalArchiveImport.upsert_into_legal_archive
        LegalArchiveImport.upsert_into_legal_archive = MagicMock()

        for item in self.archive_items:
            archive_publish.patch(item["_id"], {"headline": "publishing", "abstract": "publishing"})

        for item in self.archive_items:
            legal_item = legal_archive.find_one(req=None, _id=item["_id"])
            self.assertIsNone(legal_item, "Item: {} is not none.".format(item["_id"]))

        archive_correct.patch(self.archive_items[1]["_id"], {"headline": "correcting", "abstract": "correcting"})

        LegalArchiveImport.upsert_into_legal_archive = self.original_method
        self.class_under_test().run(1)

        # items are not expired
        for item in self.archive_items:
            legal_item = legal_archive.find_one(req=None, _id=item["_id"])
            self.assertIsNone(legal_item, "Item: {} is not none.".format(item["_id"]))

        # expire the items
        for item in self.archive_items:
            original = archive.find_one(req=None, _id=item["_id"])
            archive.system_update(item["_id"], {"expiry": utcnow() - timedelta(minutes=30)}, original)
            published.update_published_items(item["_id"], "expiry", utcnow() - timedelta(minutes=30))

        # run the command after expiry
        self.class_under_test().run(1)

        # items are expired
        for item in self.archive_items:
            legal_item = legal_archive.find_one(req=None, _id=item["_id"])
            self.assertEqual(legal_item["_id"], item["_id"], "item {} not imported to legal".format(item["_id"]))

        # items are moved to legal
        for item in self.archive_items:
            published_items = list(published.get_other_published_items(item["_id"]))
            for published_item in published_items:
                self.assertEqual(published_item["moved_to_legal"], True)

        # items are moved to legal publish queue
        for item in self.archive_items:
            req = ParsedRequest()
            req.where = json.dumps({"item_id": item["_id"]})
            queue_items = list(publish_queue.get(req=req, lookup=None))
            self.assertGreaterEqual(len(queue_items), 1)
            for queue_item in queue_items:
                self.assertEqual(queue_item["moved_to_legal"], True)

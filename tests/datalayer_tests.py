# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import superdesk

from bson import ObjectId
from superdesk.tests import TestCase
from superdesk.datalayer import SuperdeskJSONEncoder
from superdesk.errors import SuperdeskApiError, UpdateConflictError
from superdesk.utc import utcnow
from eve.io.base import DataLayer
from datetime import timedelta
from unittest.mock import patch


class DatalayerTestCase(TestCase):
    def test_system_update_checked_preserves_etag_and_indexes(self):
        service = superdesk.get_resource_service("archive")
        before = utcnow() - timedelta(days=1)
        self.app.data.insert("archive", [{"_id": "checked", "_etag": "original", "_updated": before}])
        original = service.find_one(None, _id="checked")
        now = utcnow()
        with patch("superdesk.eve_backend.utcnow", return_value=now):
            service.system_update("checked", {"slugline": "updated"}, original, check_etag=True)
        for stored in (
            service.find_one(None, _id="checked"),
            self.app.data.elastic.find_one("archive", None, _id="checked"),
        ):
            self.assertEqual("original", stored["_etag"])
            self.assertEqual(now, stored["_updated"])
            self.assertEqual("updated", stored["slugline"])
        self.assertEqual(before, original["_updated"])

    def test_system_update_checked_conflict_does_not_notify_or_index(self):
        service = superdesk.get_resource_service("archive")
        self.app.data.insert("archive", [{"_id": "checked", "_etag": "original"}])
        original = service.find_one(None, _id="checked")
        service.system_update("checked", {"_etag": "changed"}, original)
        with patch.object(self.app.data.elastic, "update") as index:
            with patch.object(service.backend, "_push_resource_notification") as notify:
                with self.assertRaises(UpdateConflictError) as caught:
                    service.system_update("checked", {"slugline": "stale"}, original, check_etag=True)
        self.assertEqual("archive", caught.exception.resource)
        self.assertEqual("checked", caught.exception.item_id)
        self.assertIsInstance(caught.exception.__cause__, DataLayer.OriginalChangedError)
        self.assertIn("archive", str(caught.exception))
        self.assertIn("checked", str(caught.exception))
        index.assert_not_called()
        notify.assert_not_called()
        self.assertNotIn("slugline", service.find_one(None, _id="checked"))

    def test_system_update_default_still_allows_stale_original(self):
        service = superdesk.get_resource_service("archive")
        self.app.data.insert("archive", [{"_id": "checked", "_etag": "original"}])
        original = service.find_one(None, _id="checked")
        service.system_update("checked", {"_etag": "changed"}, original)
        service.system_update("checked", {"slugline": "updated"}, original)
        stored = service.find_one(None, _id="checked")
        self.assertEqual("changed", stored["_etag"])
        self.assertEqual("updated", stored["slugline"])

    def test_system_update_checked_supports_change_request(self):
        service = superdesk.get_resource_service("archive")
        self.app.data.insert("archive", [{"_id": "checked", "_etag": "original", "priority": 1}])
        original = service.find_one(None, _id="checked")
        service.system_update("checked", {"$inc": {"priority": 1}}, original, change_request=True, check_etag=True)
        self.assertEqual(2, service.find_one(None, _id="checked")["priority"])

    def test_system_update_checked_noop_raises_backend_conflict(self):
        service = superdesk.get_resource_service("archive")
        self.app.data.insert("archive", [{"_id": "checked", "_etag": "original", "slugline": "same"}])
        original = service.find_one(None, _id="checked")
        with patch.object(service.backend, "_push_resource_notification") as notify:
            with self.assertRaises(UpdateConflictError):
                service.system_update(
                    "checked",
                    {"slugline": "same", "_updated": original["_updated"]},
                    original,
                    check_etag=True,
                    push_notification=False,
                )
        notify.assert_not_called()
        self.assertEqual("same", service.find_one(None, _id="checked")["slugline"])

    def test_system_update_checked_recreates_missing_search_document(self):
        service = superdesk.get_resource_service("archive")
        self.app.data.insert("archive", [{"_id": "checked", "_etag": "original"}])
        original = service.find_one(None, _id="checked")
        service.backend.remove_from_search("archive", original)
        service.system_update("checked", {"slugline": "updated"}, original, check_etag=True)
        stored = self.app.data.elastic.find_one("archive", None, _id="checked")
        self.assertEqual("updated", stored["slugline"])

    def test_system_update_checked_without_original_etag_uses_backend_behavior(self):
        service = superdesk.get_resource_service("archive")
        collection = service.backend.get_mongo_collection("archive")
        collection.insert_one({"_id": "checked", "_updated": utcnow()})
        original = collection.find_one({"_id": "checked"})
        collection.update_one({"_id": "checked"}, {"$set": {"_etag": "new"}})
        service.system_update("checked", {"slugline": "updated"}, original, check_etag=True)
        self.assertEqual("updated", collection.find_one({"_id": "checked"})["slugline"])

    def test_find_all(self):
        data = {"name": "test", "privileges": {"ingest": 1, "archive": 1, "fetch": 1}}
        superdesk.get_resource_service("roles").post([data])
        self.assertEqual(1, superdesk.get_resource_service("roles").get(req=None, lookup={}).count())

    def test_json_encoder(self):
        _id = ObjectId()
        encoder = SuperdeskJSONEncoder()
        text = encoder.dumps({"_id": _id, "name": "foo", "group": None})
        self.assertIn('"name":"foo"', text)
        self.assertIn('"group":null', text)
        self.assertIn('"_id":"%s"' % (_id,), text)

    def test_find_with_mongo_query(self):
        service = superdesk.get_resource_service("activity")
        service.post(
            [
                {"resource": "foo", "action": "get"},
                {"resource": "bar", "action": "post"},
            ]
        )

        self.assertEqual(1, service.find({"resource": {"$in": ["foo"]}}).count())
        self.assertEqual(1, service.find({}, max_results=1).count(True))

    def test_set_custom_etag_on_create(self):
        service = superdesk.get_resource_service("activity")
        ids = service.post([{"resource": "foo", "action": "get", "_etag": "foo"}])
        item = service.find_one(None, _id=ids[0])
        self.assertEqual("foo", item["_etag"])

    def test_find_one_type(self):
        self.app.data.insert("archive", [{"guid": "foo"}])
        item = self.app.data.find_one("archive", req=None, guid="foo")
        self.assertIsNotNone(item)
        self.assertEqual("archive", item.get("_type"))

    def test_get_all_batch(self):
        SIZE = 500
        items = []
        for i in range(SIZE):
            items.append({"_id": "test-{:04d}".format(i)})
        service = superdesk.get_resource_service("archive")
        service.create(items)
        counter = 0
        for item in service.get_all_batch(size=5):
            assert item["_id"] == "test-{:04d}".format(counter)
            counter += 1
        assert counter == SIZE

    def test_delete_chunks(self):
        items = []
        for i in range(5000):  # must be larger than 1k
            items.append({"_id": ObjectId()})
        service = superdesk.get_resource_service("audit")
        service.create(items)
        service.delete({})
        assert 0 == service.find({}).count()

    def test_get_all_batch_elastic(self):
        expected_item_count = 500
        items = []
        for i in range(expected_item_count):
            items.append(
                {
                    "_id": "test-{:04d}".format(i),
                    "guid": "test-{:04d}".format(i),
                }
            )
        service = superdesk.get_resource_service("archive")
        service.create(items)

        # Use custom sort, as all items would have the same ``_created`` and ``_updated`` values
        query = {"sort": [{"_created": "asc"}, {"_updated": "asc"}, {"guid": "asc"}]}
        counter = 0
        for item in service.get_all_batch_elastic(query, size=5):
            assert item["_id"] == "test-{:04d}".format(counter)
            counter += 1
        assert counter == expected_item_count

    def test_get_all_batch_elastic_required_sort_field(self):
        service = superdesk.get_resource_service("archive")

        with self.assertRaises(SuperdeskApiError) as ctx:
            service.get_all_batch_elastic({}).send(None)

        self.assertEqual(ctx.exception.status_code, 400)  # bad request error

    def test_get_all_batch_elastic_with_lookup(self):
        expected_item_count = 20
        matching = []
        other = []
        for i in range(expected_item_count):
            matching.append({"_id": f"match-{i:04d}", "guid": f"match-{i:04d}", "slugline": "keep"})
            other.append({"_id": f"skip-{i:04d}", "guid": f"skip-{i:04d}", "slugline": "drop"})

        service = superdesk.get_resource_service("archive")
        service.create(matching + other)

        query = {
            "query": {"match": {"slugline": "keep"}},
            # Use custom sort, as all items would have the same ``_created`` and ``_updated`` values
            "sort": [{"_created": "asc"}, {"_updated": "asc"}, {"guid": "asc"}],
        }
        seen = []
        for item in service.get_all_batch_elastic(query, size=5):
            seen.append(item)

        assert len(seen) == expected_item_count
        assert all(doc["slugline"] == "keep" for doc in seen)
        # ensure we did not accidentally yield items from the other slugline
        assert all(not doc["_id"].startswith("skip-") for doc in seen)

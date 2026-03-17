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


class DatalayerTestCase(TestCase):
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

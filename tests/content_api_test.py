from apps.archive.usage import update_refs
import io
import time
import superdesk

from bson import ObjectId
from copy import copy
from flask import json, request
from datetime import timedelta
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from content_api.publish import MONGO_PREFIX
from content_api.app import get_app
from eve.utils import ParsedRequest
from eve.methods.common import store_media_files
from werkzeug.datastructures import MultiDict


class ContentAPITestCase(TestCase):
    def setUp(self):
        self.content_api = superdesk.get_resource_service("content_api")
        self.db = self.app.data.mongo.pymongo(prefix=MONGO_PREFIX).db
        self.app.config["SECRET_KEY"] = "secret"
        config = copy(self.app.config)
        config["AMAZON_CONTAINER_NAME"] = None  # force gridfs
        config["URL_PREFIX"] = ""
        config["MEDIA_PREFIX"] = "/assets"
        self.capi = get_app(config)
        self.capi.testing = True
        self.subscriber = {"_id": "sub1"}

    def _auth_headers(self, sub=None):
        if sub is None:
            sub = self.subscriber
        service = superdesk.get_resource_service("subscriber_token")
        payload = {"subscriber": sub.get("_id")}
        service.create([payload])
        token = payload["_id"]
        headers = {"Authorization": "Token " + token}
        return headers

    def test_publish_to_content_api(self):
        item = {"guid": "foo", "type": "text", "task": {"desk": "foo"}, "rewrite_of": "bar"}
        self.content_api.publish(item)
        self.assertEqual(1, self.db.items.count())
        self.assertNotIn("task", self.db.items.find_one())
        self.assertEqual("foo", self.db.items.find_one()["_id"])

        item["_current_version"] = "2"
        self.content_api.publish(item)
        self.assertEqual(1, self.db.items.count())

        item["_current_version"] = "3"
        item["headline"] = "foo"
        self.content_api.publish(item)
        self.assertEqual("foo", self.db.items.find_one()["headline"])
        self.assertEqual("bar", self.db.items.find_one()["evolvedfrom"])

        self.assertEqual(3, self.db.items_versions.count())

    def test_create_keeps_planning_metadata(self):
        item = {
            "guid": "foo",
            "type": "text",
            "planning_id": "planning-id",
            "coverage_id": "coverage-id",
            "agenda_id": "agenda-id",
        }
        self.content_api.create([item])
        self.assertEqual(item["planning_id"], self.db.items.find_one()["planning_id"])
        self.assertEqual(item["coverage_id"], self.db.items.find_one()["coverage_id"])
        self.assertEqual(item["agenda_id"], self.db.items.find_one()["agenda_id"])

    def test_publish_with_subscriber_ids(self):
        item = {"guid": "foo", "type": "text"}
        subscribers = [{"_id": ObjectId()}, {"_id": ObjectId()}]

        self.content_api.publish(item, subscribers)
        self.assertEqual(1, self.db.items.find({"subscribers": str(subscribers[0]["_id"])}).count())
        self.assertEqual(0, self.db.items.find({"subscribers": "foo"}).count())

    def test_content_filtering_by_subscriber(self):
        subscriber = {"_id": "sub1"}
        headers = self._auth_headers(subscriber)

        self.content_api.publish({"_id": "foo", "guid": "foo", "type": "text"}, [subscriber])
        self.content_api.publish({"_id": "bar", "guid": "bar", "type": "text"}, [])
        self.content_api.publish({"_id": "pkg", "guid": "pkg", "type": "composite"}, [subscriber])
        self.content_api.publish({"_id": "pkg2", "guid": "pkg2", "type": "composite"}, [])

        with self.capi.test_client() as c:
            response = c.get("items")
            self.assertEqual(401, response.status_code)
            response = c.get("items", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(1, len(data["_items"]))
            self.assertNotIn("subscribers", data["_items"][0])
            self.assertIn("items/foo", data["_items"][0]["uri"])

            audit_entries = superdesk.get_resource_service("api_audit").get(req=None, lookup={})
            self.assertEqual(1, audit_entries.count())

            response = c.get("packages", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, len(data["_items"]))
            self.assertIn("packages/pkg", data["_items"][0]["uri"])

            audit_entries = superdesk.get_resource_service("api_audit").get(req=None, lookup={})
            self.assertEqual(2, audit_entries.count())

    def test_content_filtering_by_arguments(self):
        subscriber = {"_id": "sub1"}
        headers = self._auth_headers(subscriber)

        self.content_api.publish({"_id": "foo", "guid": "foo", "urgency": "3", "type": "text"}, [subscriber])
        self.content_api.publish({"_id": "bar", "guid": "bar", "urgency": "4", "type": "text"}, [subscriber])

        with self.capi.test_client() as c:
            response = c.get("items")
            self.assertEqual(401, response.status_code)
            response = c.get("items", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(2, len(data["_items"]))

            response = c.get('items?filter=[{"term":{"urgency": 3}}]', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(1, len(data["_items"]))

    def test_content_api_picture(self):
        self.content_api.publish(
            {
                "_id": "foo",
                "guid": "foo",
                "type": "picture",
                "headline": "foo",
                "renditions": {
                    "original": {
                        "media": "abcd1234",
                        "width": 300,
                        "height": 200,
                        "mimetype": "image/jpeg",
                        "href": "foo",
                    }
                },
            }
        )

        headers = self._auth_headers()

        with self.capi.test_client() as c:
            response = c.get("items/foo", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertIn("renditions", data)
            rendition = data["renditions"]["original"]
            self.assertNotIn("media", rendition)
            self.assertIn("assets/abcd1234", rendition["href"])

            response = c.get(rendition["href"])
            self.assertEqual(401, response.status_code)

            response = c.get(rendition["href"], headers=headers)
            self.assertEqual(404, response.status_code)

            with self.app.app_context():
                data = io.BytesIO(b"content")
                media_id = self.app.media.put(data, resource="upload")
                self.assertIsInstance(media_id, ObjectId, media_id)

            url = "assets/%s" % media_id
            response = c.get(url, headers=headers)
            self.assertEqual(200, response.status_code, url)
            self.assertEqual(b"content", response.data)

            audit_entries = superdesk.get_resource_service("api_audit").get(req=None, lookup={"type": "asset"})
            self.assertEqual(1, audit_entries.count())

    def test_update_picture(self):
        picture = {
            "_id": "foo",
            "guid": "foo",
            "type": "picture",
            "headline": "foo",
            "renditions": {
                "original": {
                    "media": "abcd1234",
                    "width": 300,
                    "height": 200,
                    "mimetype": "image/jpeg",
                    "href": "foo",
                },
                "thumbnail": {
                    "media": "abcd1234",
                    "width": 300,
                    "height": 200,
                    "mimetype": "image/jpeg",
                    "href": "foo",
                },
            },
        }

        self.content_api.publish(picture)

        picture["renditions"]["viewImage"] = picture["renditions"].pop("thumbnail")
        self.content_api.publish(picture)

        headers = self._auth_headers()
        with self.capi.test_client() as c:
            response = c.get("items/foo", headers=headers)
            data = json.loads(response.data)
            self.assertIn("viewImage", data["renditions"])
            self.assertNotIn("thumbnail", data["renditions"])

    def test_text_with_pic_associations(self):
        subscriber = {"_id": "sub1"}
        self.content_api.publish(
            {
                "guid": "text",
                "type": "text",
                "body_html": """<p>
            <p>hey</p>
            <!-- EMBED START Image {id: \"foo\"} -->
            <figure>
                <img src=\"http://localhost:5000/api/upload/foo/raw?_schema=http\"
                    alt=\"tractor\"
                    srcset=\"//localhost:5000/api/upload/foo/raw?_schema=http 800w\" />
                <figcaption>tractor</figcaption>
            </figure>
            <!-- EMBED END Image {id: \"embedded12554054581\"} -->
            """,
                "associations": {
                    "foo": {
                        "type": "picture",
                        "renditions": {
                            "original": {
                                "href": "http://localhost:5000/api/upload/foo/raw?_schema=http",
                                "media": "bar",
                            }
                        },
                        "subscribers": ["sub1"],
                    },
                },
            },
            [subscriber],
        )

        headers = self._auth_headers(subscriber)
        with self.capi.test_client() as c:
            response = c.get("items/text", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, len(data["associations"]))
            renditions = data["associations"]["foo"]["renditions"]
            self.assertIn("assets/bar", renditions["original"]["href"])
            self.assertNotIn("http://localhost:5000/api/upload/", data["body_html"])

    def test_association_update(self):
        subscribers = [self.subscriber["_id"]]
        self.content_api.publish(
            {
                "guid": "text",
                "type": "text",
                "body_html": "",
                "version": 1,
                "associations": {
                    "foo": {
                        "guid": "foo",
                        "type": "picture",
                        "renditions": {
                            "original": {
                                "media": "abcd1234",
                                "width": 300,
                                "height": 200,
                                "mimetype": "image/jpeg",
                                "href": "foo",
                            },
                            "viewImage": {
                                "media": "abcd1234",
                                "width": 300,
                                "height": 200,
                                "mimetype": "image/jpeg",
                                "href": "foo",
                            },
                        },
                        "subscribers": subscribers,
                    },
                },
            },
            [self.subscriber],
        )

        data = self.get_json("items/text")
        picture = data["associations"]["foo"]
        self.assertIn("viewImage", picture["renditions"])

        self.content_api.publish(
            {
                "guid": "text",
                "type": "text",
                "body_html": "",
                "version": 2,
                "associations": {
                    "foo": {
                        "guid": "bar",
                        "type": "picture",
                        "renditions": {
                            "original": {
                                "media": "abcd1234",
                                "width": 300,
                                "height": 200,
                                "mimetype": "image/jpeg",
                                "href": "bar",
                            },
                            "baseImage": {
                                "media": "abcd1234",
                                "width": 300,
                                "height": 200,
                                "mimetype": "image/jpeg",
                                "href": "bar",
                            },
                        },
                        "subscribers": subscribers,
                    },
                },
            },
            [self.subscriber],
        )

        data = self.get_json("items/text")
        picture = data["associations"]["foo"]
        self.assertNotIn("viewImage", picture["renditions"])
        self.assertIn("baseImage", picture["renditions"])

        self.content_api.publish(
            {
                "guid": "text",
                "type": "text",
                "body_html": "updated",
                "version": 3,
            },
            [self.subscriber],
        )

        data = self.get_json("items/text")
        self.assertEqual({}, data["associations"])

    def get_json(self, url, subscriber=None):
        headers = self._auth_headers(subscriber)
        with self.capi.test_client() as c:
            response = c.get(url, headers=headers)
            data = json.loads(response.data)
            return data

    def test_content_filtering(self):
        item = {
            "guid": "u3",
            "type": "text",
            "source": "foo",
            "urgency": 3,
            "associations": {
                "one": {"guid": "u2", "type": "text", "source": "bar"},
                "two": {"guid": "u1", "type": "text", "source": "baz"},
            },
        }

        update_refs(item, {})

        self.content_api.publish(item, [self.subscriber])
        self.content_api.publish({"guid": "u2", "type": "text", "source": "bar", "urgency": 2}, [self.subscriber])

        headers = self._auth_headers()

        with self.capi.test_client() as c:
            response = c.get('items?where={"urgency":3}', headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, data["_meta"]["total"])
            self.assertEqual(3, data["_items"][0]["urgency"])

            response = c.get("items?q=urgency:3", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, data["_meta"]["total"])
            self.assertEqual(3, data["_items"][0]["urgency"])

            response = c.get("items?urgency=3", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, data["_meta"]["total"])
            self.assertEqual(3, data["_items"][0]["urgency"])

            response = c.get("items?urgency=[3,2]", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(2, data["_meta"]["total"])

            response = c.get("items?item_source=foo", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, data["_meta"]["total"])
            self.assertEqual("foo", data["_items"][0]["source"])

            response = c.get('items?item_source=["foo","bar"]', headers=headers)
            data = json.loads(response.data)
            self.assertEqual(2, data["_meta"]["total"])

            response = c.get("items?related_to=u2", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(1, data["_meta"]["total"])

            response = c.get("items?related_to=empty", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(0, data["_meta"]["total"])

            response = c.get("items?related_source=bar", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(1, data["_meta"]["total"])

            response = c.get("items?related_source=empty", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(0, data["_meta"]["total"])

    def test_generate_token_service(self):
        service = superdesk.get_resource_service("subscriber_token")
        payload = {"subscriber": "foo", "expiry_days": 7}
        ids = service.create([payload])
        token = payload["_id"]
        self.assertEqual("foo", self.capi.auth.check_auth(token, [], "items", "get"))
        self.assertLessEqual((utcnow() + timedelta(days=7)).timestamp() - payload["expiry"].timestamp(), 1)

        service.delete({"_id": ids[0]})
        self.assertFalse(self.capi.auth.check_auth(token, [], "items", "get"))

        payload = {"subscriber": "foo", "expiry": utcnow() - timedelta(days=1)}
        service.create([payload])
        token = payload["_id"]
        self.assertFalse(self.capi.auth.check_auth(token, [], "items", "get"))
        self.assertIsNone(service.find_one(None, _id=token))

    def test_api_block(self):
        self.app.data.insert(
            "filter_conditions", [{"_id": 1, "operator": "eq", "field": "source", "value": "fred", "name": "Fred"}]
        )
        content_filter = {
            "_id": 1,
            "name": "fred API Block",
            "content_filter": [{"expression": {"fc": [1]}}],
            "api_block": True,
        }
        self.app.data.insert("content_filters", [content_filter])

        self.content_api.publish({"_id": "foo", "source": "fred", "type": "text", "guid": "foo"})
        self.assertEqual(0, self.db.items.count())
        self.content_api.publish({"_id": "bar", "source": "jane", "type": "text", "guid": "bar"})
        self.assertEqual(1, self.db.items.count())

    def test_item_versions_api(self):
        subscriber = {"_id": "sub1"}
        headers = self._auth_headers(subscriber)

        item = {"guid": "foo", "type": "text", "task": {"desk": "foo"}, "rewrite_of": "bar", "_current_version": 1}
        self.content_api.publish(item, [subscriber])
        item["_current_version"] = 2
        self.content_api.publish(item, [subscriber])
        item["_current_version"] = 3
        self.content_api.publish(item, [subscriber])

        with self.capi.test_client() as c:
            response = c.get("items/foo?version=all", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(3, data["_meta"]["total"])

            response = c.get("items/foo?version=2", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(str(2), data["version"])

    def test_package_version(self):
        subscriber = {"_id": "sub1"}
        headers = self._auth_headers(subscriber)

        item = {"_id": "pkg", "guid": "pkg", "type": "composite", "_current_version": 1}
        self.content_api.publish(item, [subscriber])
        item["_current_version"] = 2
        self.content_api.publish(item, [subscriber])
        item["_current_version"] = 3
        self.content_api.publish(item, [subscriber])
        item = {"guid": "foo", "type": "text", "task": {"desk": "foo"}, "rewrite_of": "bar", "_current_version": 1}
        self.content_api.publish(item, [subscriber])

        with self.capi.test_client() as c:
            response = c.get("packages", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, len(data["_items"]))
            self.assertIn("packages/pkg", data["_items"][0]["uri"])

            response = c.get("packages/pkg?version=all", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(3, data["_meta"]["total"])

            response = c.get("packages/pkg?version=2", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(str(2), data["version"])

    def test_publish_kill_to_content_api(self):
        subscriber = {"_id": "sub1"}
        headers = self._auth_headers(subscriber)
        item = {"guid": "foo", "type": "text", "task": {"desk": "foo"}, "rewrite_of": "bar", "pubstatus": "usable"}
        self.content_api.publish(item, [subscriber])

        with self.capi.test_client() as c:
            response = c.get("items/foo?version=all", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, data["_meta"]["total"])

            response = c.get("items/foo?version=1", headers=headers)
            data = json.loads(response.data)
            self.assertEqual("1", data["version"])

        item["pubstatus"] = "canceled"
        item["_current_version"] = 2
        self.content_api.publish(item, [subscriber])

        self.assertEqual(1, self.db.items.count())
        self.assertEqual("canceled", self.db.items.find_one()["pubstatus"])
        self.assertEqual(2, self.db.items_versions.count())
        for i in self.db.items_versions.find():
            self.assertEqual(i.get("pubstatus"), "canceled")

        with self.capi.test_client() as c:
            response = c.get("items/foo?version=all", headers=headers)
            data = json.loads(response.data)
            self.assertEqual(0, data["_meta"]["total"])

            response = c.get("items/foo?version=1", headers=headers)
            self.assertEqual(404, response._status_code)

    def test_publish_item_with_ancestors(self):
        item = {"guid": "foo", "type": "text", "task": {"desk": "foo"}, "bookmarks": [ObjectId()]}
        self.content_api.publish(item)
        self.assertEqual(1, self.db.items.count())
        self.assertNotIn("ancestors", self.db.items.find_one({"_id": "foo"}))

        item["guid"] = "bar"
        item["rewrite_of"] = "foo"
        self.content_api.publish(item)

        self.assertEqual(2, self.db.items.count())
        bar = self.db.items.find_one({"_id": "bar"})
        self.assertEqual(["foo"], bar.get("ancestors", []))
        self.assertEqual("foo", bar.get("evolvedfrom"))
        foo = self.db.items.find_one({"_id": "foo"})
        self.assertEqual("bar", foo["nextversion"])

        item["guid"] = "fun"
        item["rewrite_of"] = "bar"
        self.content_api.publish(item)

        self.assertEqual(3, self.db.items.count())
        fun = self.db.items.find_one({"_id": "fun"})
        self.assertEqual(["foo", "bar"], fun.get("ancestors", []))
        self.assertEqual("bar", fun.get("evolvedfrom"))

    def test_sync_bookmarks_on_publish(self):
        item = {"guid": "foo", "type": "text", "task": {"desk": "foo"}}
        self.content_api.publish(item)
        self.db.items.update_one({"_id": "foo"}, {"$set": {"bookmarks": [ObjectId()]}})

        item["guid"] = "bar"
        item["rewrite_of"] = "foo"
        self.content_api.publish(item)

        bar = self.db.items.find_one({"_id": "bar"})
        self.assertEqual(1, len(bar["bookmarks"]))

    def test_search_capi(self):
        subscriber = {"_id": "sub1"}

        self.content_api.publish(
            {
                "_id": "foo",
                "guid": "foo",
                "type": "text",
                "anpa_category": [{"qcode": "i", "name": "International News"}],
                "headline": "Man bites dog",
            },
            [subscriber],
        )
        self.content_api.publish({"_id": "bar", "guid": "bar", "type": "text"}, [{"_id": "sub2"}])

        test = superdesk.get_resource_service("search_capi")
        req = ParsedRequest()
        req.args = MultiDict([("subscribers", "sub1")])
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.count(), 1)

        resp = test.get(req=None, lookup=None)
        self.assertEqual(resp.count(), 2)

        req = ParsedRequest()
        req.args = MultiDict()
        req.where = '{"headline":"dog"}'
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.count(), 1)

    def test_search_capi_filter(self):
        subscriber = {"_id": "sub1"}

        self.content_api.publish(
            {
                "_id": "foo",
                "guid": "foo",
                "type": "text",
                "anpa_category": [{"qcode": "i", "name": "International News"}],
                "headline": "Man bites dog",
            },
            [subscriber],
        )
        self.content_api.publish(
            {
                "_id": "bar",
                "guid": "bar",
                "anpa_category": [{"qcode": "i", "name": "International News"}],
                "type": "text",
            },
            [{"_id": "sub2"}],
        )
        self.content_api.publish(
            {"_id": "nat", "guid": "nat", "anpa_category": [{"qcode": "a", "name": "National News"}], "type": "text"},
            [{"_id": "sub2"}],
        )

        test = superdesk.get_resource_service("search_capi")
        req = ParsedRequest()
        req.args = MultiDict([("filter", '[{"term": {"service.code": "i"}}]')])
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.count(), 2)
        self.assertEqual(resp.docs[0].get("anpa_category")[0].get("qcode"), "i")
        self.assertEqual(resp.docs[1].get("anpa_category")[0].get("qcode"), "i")

        req = ParsedRequest()
        req.args = MultiDict([("service", "i")])
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.count(), 2)
        self.assertEqual(resp.docs[0].get("anpa_category")[0].get("qcode"), "i")
        self.assertEqual(resp.docs[1].get("anpa_category")[0].get("qcode"), "i")

        req = ParsedRequest()
        req.args = MultiDict([("service", '["a"]')])
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.count(), 1)
        self.assertEqual(resp.docs[0].get("anpa_category")[0].get("qcode"), "a")

        req = ParsedRequest()
        req.args = MultiDict([("service", "i"), ("subscribers", "sub1")])
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.count(), 1)
        self.assertEqual(resp.docs[0].get("anpa_category")[0].get("qcode"), "i")
        self.assertEqual(resp.docs[0].get("subscribers")[0], "sub1")

        req = ParsedRequest()
        req.args = MultiDict([("subscribers", "sub2")])
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.count(), 2)
        self.assertEqual(resp.docs[0].get("subscribers")[0], "sub2")
        self.assertEqual(resp.docs[1].get("subscribers")[0], "sub2")

    def test_search_capi_aggregations(self):
        self.content_api.publish(
            {
                "_id": "1",
                "guid": "1",
                "type": "text",
                "anpa_category": [{"qcode": "i", "name": "International News"}],
                "headline": "Man bites dog",
                "source": "AAA",
                "urgency": 1,
            },
            [],
        )
        self.content_api.publish(
            {
                "_id": "2",
                "guid": "2",
                "type": "text",
                "anpa_category": [{"qcode": "i", "name": "International News"}],
                "headline": "Man bites cat",
                "source": "BBB",
                "urgency": 2,
            },
            [],
        )

        test = superdesk.get_resource_service("search_capi")
        req = ParsedRequest()
        req.args = MultiDict([("aggregations", 1)])
        resp = test.get(req=req, lookup=None)
        self.assertEqual(resp.hits["aggregations"]["category"]["buckets"][0]["doc_count"], 2)

    def test_associated_item_filter_by_subscriber(self):
        item = {
            "guid": "foo",
            "type": "text",
            "task": {"desk": "foo"},
            "associations": {"featuremedia": {"guid": "a1", "type": "picture", "subscribers": ["sub1"]}},
        }
        subscriber1 = {"_id": "sub1"}
        subscriber2 = {"_id": "sub2"}
        self.content_api.publish(item, [subscriber1, subscriber2])
        self.assertEqual(1, self.db.items.count())
        with self.capi.test_client() as c:
            response = c.get("items/foo", headers=self._auth_headers(subscriber1))
            data = json.loads(response.data)
            self.assertIn("items/foo", data["uri"])
            self.assertEqual(data["associations"]["featuremedia"]["guid"], "a1")

            response = c.get("items/foo", headers=self._auth_headers(subscriber2))
            data = json.loads(response.data)
            self.assertIn("items/foo", data["uri"])
            self.assertNotIn("featuremedia", data["associations"])

    def test_publish_item_with_attachments(self):
        media = io.BytesIO(b"content")
        data = {"media": (media, "media.txt")}
        attachment = {"title": "Test", "description": "test"}
        with self.app.test_request_context("attachments", method="POST", data=data):
            attachment["media"] = request.files["media"]
            store_media_files(attachment, "attachments")  # this would happen automatically otherwise
            superdesk.get_resource_service("attachments").post([attachment])
        self.assertIn("_id", attachment)
        self.assertIsInstance(attachment["media"], ObjectId)

        item = {
            "guid": "foo",
            "type": "text",
            "attachments": [{"attachment": attachment["_id"]}],
            "body_html": '<p><a data-attachment="{}">download</a></p>'.format(str(attachment["_id"])),
        }

        subscriber = {"_id": "sub"}
        self.content_api.publish(item, [subscriber])
        with self.capi.test_client() as c:
            response = c.get("items/foo", headers=self._auth_headers(subscriber))
            data = json.loads(response.data)

        self.assertIn("attachments", data)
        attachments = data["attachments"]
        self.assertEqual(1, len(attachments))
        self.assertEqual("Test", attachments[0]["title"])
        self.assertEqual("test", attachments[0]["description"])
        self.assertEqual("media.txt", attachments[0]["filename"])
        self.assertEqual("text/plain", attachments[0]["mimetype"])
        self.assertEqual(7, attachments[0]["length"])
        self.assertIn("href", attachments[0])
        self.assertIn("media", attachments[0])
        self.assertIn('data-attachment="{}"'.format(attachments[0]["id"]), data["body_html"])

        with self.capi.test_client() as c:
            response = c.get(attachments[0]["href"], headers=self._auth_headers(subscriber))
            self.assertEqual(200, response.status_code, attachments[0]["href"])

    def test_publish_item_with_internal_attachments(self):
        media = io.BytesIO(b"content")
        data = {"media": (media, "media.txt")}
        internal_attachment = {"title": "Test Internal", "description": "test", "internal": True}
        public_attachment = {"title": "Test", "description": "test", "internal": False}
        with self.app.test_request_context("attachments", method="POST", data=data):
            internal_attachment["media"] = request.files["media"]
            public_attachment["media"] = request.files["media"]
            store_media_files(internal_attachment, "attachments")
            store_media_files(public_attachment, "attachments")
            superdesk.get_resource_service("attachments").post([internal_attachment, public_attachment])
        self.assertIn("_id", internal_attachment)
        self.assertIn("_id", public_attachment)
        self.assertIsInstance(internal_attachment["media"], ObjectId)
        self.assertIsInstance(public_attachment["media"], ObjectId)

        item = {
            "guid": "foo-internal",
            "type": "text",
            "attachments": [{"attachment": internal_attachment["_id"]}, {"attachment": public_attachment["_id"]}],
            "body_html": "<p>Foo Bar</p>",
        }

        subscriber = {"_id": "sub"}
        self.content_api.publish(item, [subscriber])
        with self.capi.test_client() as c:
            response = c.get("items/foo-internal", headers=self._auth_headers(subscriber))
            data = json.loads(response.data)

        self.assertIn("attachments", data)
        attachments = data["attachments"]
        # there should be only one attachment (public one)
        self.assertEqual(1, len(attachments))
        self.assertEqual(str(public_attachment["_id"]), attachments[0]["id"])

    def test_items_default_sorting(self):
        subscriber = {"_id": "sub1"}
        headers = self._auth_headers(subscriber)

        self.content_api.publish(
            {"_id": "aaaa", "guid": "aaa", "urgency": "1", "type": "text", "source": "foo"}, [subscriber]
        )
        # We want to test a default sorting and default sort field is versioncreated,
        # so if we `self.content_api.publish` without delay, `versioncreated` will be almost the same, because it
        # filled automatically in publish service.
        # The lowest dimension is a `second` in datetime format for `versioncreated`.
        # That's why 1 sec delay is used.
        time.sleep(1)
        self.content_api.publish(
            {"_id": "bbbb", "guid": "bbb", "urgency": "2", "type": "text", "source": "foo"}, [subscriber]
        )
        time.sleep(1)
        self.content_api.publish(
            {"_id": "cccc", "guid": "ccc", "urgency": "3", "type": "text", "source": "foo"}, [subscriber]
        )
        time.sleep(1)
        self.content_api.publish(
            {"_id": "dddd", "guid": "ddd", "urgency": "4", "type": "text", "source": "bar"}, [subscriber]
        )
        time.sleep(1)
        self.content_api.publish(
            {"_id": "eeee", "guid": "eee", "urgency": "5", "type": "text", "source": "foo"}, [subscriber]
        )

        with self.capi.test_client() as c:
            # no filters
            response = c.get("items", headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertListEqual([i["urgency"] for i in data["_items"]], ["5", "4", "3", "2", "1"])

            # with filtering
            response = c.get('items?item_source=["foo"]', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertListEqual([i["urgency"] for i in data["_items"]], ["5", "3", "2", "1"])

            # with filtering and custom sorting
            response = c.get('items?item_source=["foo"]&sort=[("versioncreated",1)]', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertListEqual([i["urgency"] for i in data["_items"]], ["1", "2", "3", "5"])

    def test_items_custom_sorting(self):
        subscriber = {"_id": "sub1"}
        headers = self._auth_headers(subscriber)

        self.content_api.publish(
            {"_id": "aaaa", "guid": "aaa", "urgency": "1", "type": "text", "source": "foo"}, [subscriber]
        )
        self.content_api.publish(
            {"_id": "bbbb", "guid": "bbb", "urgency": "2", "type": "text", "source": "foo"}, [subscriber]
        )
        self.content_api.publish(
            {"_id": "cccc", "guid": "ccc", "urgency": "3", "type": "text", "source": "foo"}, [subscriber]
        )
        self.content_api.publish(
            {"_id": "dddd", "guid": "ddd", "urgency": "4", "type": "text", "source": "bar"}, [subscriber]
        )
        self.content_api.publish(
            {"_id": "eeee", "guid": "eee", "urgency": "5", "type": "text", "source": "foo"}, [subscriber]
        )

        with self.capi.test_client() as c:
            # urgency desc
            response = c.get('items?sort=[("urgency",-1)]', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertListEqual([i["urgency"] for i in data["_items"]], ["5", "4", "3", "2", "1"])

            # urgency asc
            response = c.get('items?sort=[("urgency",1)]', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertListEqual([i["urgency"] for i in data["_items"]], ["1", "2", "3", "4", "5"])

            # urgency asc + filter
            response = c.get('items?sort=[("urgency",1)]&item_source=["foo"]', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertListEqual([i["urgency"] for i in data["_items"]], ["1", "2", "3", "5"])

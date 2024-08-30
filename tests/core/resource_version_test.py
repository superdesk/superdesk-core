from superdesk.utc import utcnow

from superdesk.tests import AsyncTestCase, AsyncFlaskTestCase

from .modules.content import ContentResourceService, Content
from .fixtures.users import john_doe


NOW = utcnow()


class TestResourceVersion(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.content", "tests.core.modules.users"]}
    service: ContentResourceService

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = ContentResourceService()

    async def test_mongo_client(self):
        # Check the mongo clients point to the same database
        content_db = self.app.mongo.get_db_async(self.service.resource_name)
        content_version_db = self.app.mongo.get_db_async(self.service.resource_name, True)

        self.assertEqual(content_db.client.address, content_version_db.client.address)
        self.assertEqual(content_db.name, content_version_db.name)

        # Now check that each collection points to the correct one
        content_client = self.app.mongo.get_collection_async(self.service.resource_name)
        self.assertEqual(content_client.name, self.service.resource_name)

        content_version_client = self.app.mongo.get_collection_async(self.service.resource_name, True)
        self.assertEqual(content_version_client.name, f"{self.service.resource_name}_versions")

        # Test attempting to get version client from resource where it's disabled
        self.app.mongo.get_client_async("users_async")
        with self.assertRaises(RuntimeError):
            self.app.mongo.get_client_async("users_async", True)

    async def test_create_versions(self, *args):
        await self.service.create([Content(id="content_1", guid="content_1", headline="Some article")])

        self.assertEqual(await self.service.mongo_versioned.count_documents({"_id_document": "content_1"}), 1)
        cursor = self.service.mongo_versioned.find({"_id_document": "content_1"})
        self.assertIsNotNone(await cursor.next())
        with self.assertRaises(StopAsyncIteration):
            await cursor.next()

        await self.service.update("content_1", dict(headline="Some article updated"))
        self.assertEqual(await self.service.mongo_versioned.count_documents({"_id_document": "content_1"}), 2)
        cursor = self.service.mongo_versioned.find({"_id_document": "content_1"})
        self.assertIsNotNone(await cursor.next())
        self.assertIsNotNone(await cursor.next())

        with self.assertRaises(StopAsyncIteration):
            await cursor.next()


class ResourceVersionEndpointsTestCase(AsyncFlaskTestCase):
    app_config = {"MODULES": ["tests.core.modules.content", "tests.core.modules.users"]}
    service: ContentResourceService

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = ContentResourceService()

    async def add_versioned_docs(self):
        response = await self.test_client.post(
            "/api/content_async",
            json=Content(
                id="content_1",
                guid="content_1",
                headline="Some article",
            ),
        )
        self.assertEqual(response.status_code, 201)

        response = await self.test_client.get("/api/content_async/content_1")
        self.assertEqual(response.status_code, 200)
        original = await response.get_json()
        self.assertEqual(original["_current_version"], 1)

        response = await self.test_client.patch(
            "/api/content_async/content_1",
            json=dict(headline="Some article updated", lock_user="user_1"),
            headers={"If-Match": original["_etag"]},
        )
        self.assertEqual(response.status_code, 200)

    async def test_rest_get_endpoint(self):
        await self.add_versioned_docs()

        response = await self.test_client.get("/api/content_async/content_1")
        self.assertEqual(response.status_code, 200)
        updated = await response.get_json()
        self.assertEqual(updated["_current_version"], 2)

        # Test getting specific version
        response = await self.test_client.get("/api/content_async/content_1?version=1")
        self.assertEqual(response.status_code, 200)
        versioned_item = await response.get_json()
        self.assertDictContains(
            versioned_item,
            dict(
                _latest_version=2,
                _current_version=1,
            ),
        )

        response = await self.test_client.get("/api/content_async/content_1?version=2")
        self.assertEqual(response.status_code, 200)
        versioned_item = await response.get_json()
        self.assertDictContains(
            versioned_item,
            dict(
                _latest_version=2,
                _current_version=2,
            ),
        )

        response = await self.test_client.get("/api/content_async/content_1?version=3")
        self.assertEqual(response.status_code, 404)

        # Test getting all versions
        response = await self.test_client.get("/api/content_async/content_1?version=all")
        self.assertEqual(response.status_code, 200)
        response = await response.get_json()
        items = response["_items"]

        self.assertDictContains(
            items[0],
            dict(
                _current_version=1,
                _latest_version=2,
                headline="Some article",
            ),
        )
        self.assertDictContains(
            items[1],
            dict(
                _current_version=2,
                _latest_version=2,
                headline="Some article updated",
            ),
        )

    async def test_version_param_validation(self):
        await self.add_versioned_docs()

        response = await self.test_client.get("/api/content_async/content_1?version=1")
        self.assertEqual(response.status_code, 200)

        response = await self.test_client.get("/api/content_async/content_1?version=all")
        self.assertEqual(response.status_code, 200)

        response = await self.test_client.get("/api/content_async/content_1?version=0")
        self.assertEqual(response.status_code, 404)

        response = await self.test_client.get("/api/content_async/content_1?version=blah")
        self.assertEqual(response.status_code, 400)

        response = await self.test_client.get("/api/content_async/content_1?version=")
        self.assertEqual(response.status_code, 400)

        response = await self.test_client.get("/api/content_async/content_1?version=-1")
        self.assertEqual(response.status_code, 400)

    async def test_request_validation_when_versioning_disabled(self):
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        response = await self.test_client.get(f"/api/users_async/{test_user.id}")
        self.assertEqual(response.status_code, 200)

        response = await self.test_client.get(f"/api/users_async/{test_user.id}?version=1")
        self.assertEqual(response.status_code, 400)

        response = await self.test_client.get(f"/api/users_async/{test_user.id}?version=all")
        self.assertEqual(response.status_code, 400)

    async def test_version_ignore_fields(self):
        await self.add_versioned_docs()

        # Test getting specific version
        response = await self.test_client.get("/api/content_async/content_1?version=1")
        self.assertDictContains(
            await response.get_json(),
            dict(
                _latest_version=2,
                _current_version=1,
                lock_user="user_1",
            ),
        )

        response = await self.test_client.get("/api/content_async/content_1?version=2")
        self.assertDictContains(
            await response.get_json(),
            dict(
                _latest_version=2,
                _current_version=2,
                lock_user="user_1",
            ),
        )

        # Test getting all versions
        response = await self.test_client.get("/api/content_async/content_1?version=all")
        items = (await response.get_json())["_items"]
        self.assertDictContains(
            items[0],
            dict(
                _current_version=1,
                _latest_version=2,
                lock_user="user_1",
            ),
        )
        self.assertDictContains(
            items[1],
            dict(
                _current_version=2,
                _latest_version=2,
                lock_user="user_1",
            ),
        )

    async def test_versioned_hateoas(self):
        await self.add_versioned_docs()

        # Test getting all versions in the one request
        response = await self.test_client.get("/api/content_async/content_1?version=all")
        json_data = await response.get_json()
        self.assertEqual(len(json_data["_items"]), 2)
        self.assertDictContains(
            json_data["_meta"],
            dict(
                max_results=200,
                page=1,
                total=2,
            ),
        )
        self.assertDictContains(
            json_data["_links"],
            dict(
                self=dict(
                    href="api/content_async/content_1?version=all",
                    title="Content",
                ),
            ),
        )
        self.assertIsNone(json_data["_links"].get("next"))
        self.assertIsNone(json_data["_links"].get("last"))

        # Test pagination - Page 1
        response = await self.test_client.get("/api/content_async/content_1?max_results=1&version=all")
        json_data = await response.get_json()
        items = json_data["_items"]
        self.assertEqual(len(items), 1)
        self.assertDictContains(
            items[0],
            dict(
                _current_version=1,
                _latest_version=2,
            ),
        )
        self.assertDictContains(
            json_data["_meta"],
            dict(
                max_results=1,
                page=1,
                total=2,
            ),
        )
        self.assertDictContains(
            json_data["_links"],
            dict(
                self=dict(
                    href="api/content_async/content_1?max_results=1&version=all",
                    title="Content",
                ),
                next=dict(
                    href="api/content_async/content_1?max_results=1&version=all&page=2",
                    title="next page",
                ),
                last=dict(
                    href="api/content_async/content_1?max_results=1&version=all&page=2",
                    title="last page",
                ),
            ),
        )

        # Test pagination - Page 2
        response = await self.test_client.get("/api/content_async/content_1?max_results=1&version=all&page=2")
        json_data = await response.get_json()
        items = json_data["_items"]
        self.assertEqual(len(items), 1)
        self.assertDictContains(
            items[0],
            dict(
                _current_version=2,
                _latest_version=2,
            ),
        )
        self.assertDictContains(
            json_data["_meta"],
            dict(
                max_results=1,
                page=2,
                total=2,
            ),
        )
        self.assertDictContains(
            json_data["_links"],
            dict(
                self=dict(
                    href="api/content_async/content_1?max_results=1&version=all&page=2",
                    title="Content",
                ),
                prev=dict(
                    href="api/content_async/content_1?max_results=1&version=all",
                    title="previous page",
                ),
            ),
        )

    async def test_mongo_versioned_indexes(self):
        self.app.init_indexes()
        collection = self.async_app.mongo.get_collection_async("content_async")
        base_indexes = await collection.index_information()

        collection = self.async_app.mongo.get_collection_async("content_async", versioning=True)
        versioned_indexes = await collection.index_information()

        self.assertEqual(base_indexes.get("_id_"), versioned_indexes.get("_id_"))
        self.assertEqual(base_indexes.get("guid"), versioned_indexes.get("guid"))
        self.assertDictContains(
            versioned_indexes["_id_document_1"], dict(background=True, key=[("_id_document", 1)], sparse=True)
        )
        self.assertDictContains(
            versioned_indexes["_id_document_current_version_1"],
            dict(
                background=True,
                key=[
                    ("_id_document", 1),
                    ("_current_version", 1),
                ],
                sparse=True,
                unique=True,
            ),
        )

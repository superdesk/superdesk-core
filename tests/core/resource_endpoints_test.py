from unittest import mock
import simplejson as json

from superdesk.utc import utcnow
from superdesk.utils import format_time

from superdesk.tests.asyncio import AsyncFlaskTestCase

from .modules.users import UserResourceService
from .fixtures.users import john_doe


NOW = utcnow()


class ResourceEndpointsTestCase(AsyncFlaskTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = UserResourceService()

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_post(self, mock_utcnow):
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        # Test the User exists in MongoDB with correct data
        test_user.created = NOW
        test_user.updated = NOW
        test_user_dict = test_user.model_dump(by_alias=True, exclude_unset=True)
        mongo_item = await self.service.mongo.find_one({"_id": test_user.id})
        self.assertEqual(mongo_item, test_user_dict)

        # Test the User exists in Elasticsearch with correct data
        # (Convert the datetime values to strings, as es client doesn't convert them)
        elastic_item = await self.service.elastic.find_by_id(test_user.id)
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
            )
        )
        self.assertEqual(elastic_item, test_user_dict)

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_get_item(self, mock_utcnow):
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        response = await self.test_client.get(f"/api/users_async/{test_user.id}")
        test_user_dict = self.test_client.model_instance_to_json(test_user)
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
            )
        )
        self.assertEqual(await response.get_json(), test_user_dict)

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_patch(self, mock_utcnow):
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={
                "first_name": "Foo",
                "last_name": "Bar",
            },
        )
        self.assertEqual(response.status_code, 200)

        response = await self.test_client.get(f"/api/users_async/{test_user.id}")
        test_user_dict = self.test_client.model_instance_to_json(test_user)
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
                first_name="Foo",
                last_name="Bar",
            )
        )
        self.assertEqual(await response.get_json(), test_user_dict)

    async def test_delete(self):
        # Test resource is empty
        response = await self.test_client.get("/api/users_async")
        self.assertEqual(response.status_code, 200)
        json_data = await response.get_json()
        self.assertEqual(json_data["_items"], [])
        self.assertEqual(json_data["_meta"]["total"], 0)

        # Add a new user, and search returns it
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)
        response = await self.test_client.get("/api/users_async")
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await response.get_json())["_meta"]["total"], 1)

        # Delete the user, and make sure search is empty
        response = await self.test_client.delete(f"/api/users_async/{test_user.id}")
        self.assertEqual(response.status_code, 204)
        response = await self.test_client.get("/api/users_async")
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await response.get_json())["_meta"]["total"], 0)

        # Raises `notFoundError` is Resource with ID does not exist
        response = await self.test_client.delete(f"/api/users_async/{test_user.id}")
        self.assertEqual(response.status_code, 404)

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_search(self, mock_utcnow):
        test_user = john_doe()
        test_user_dict = self.test_client.model_instance_to_json(test_user)
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
            )
        )

        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        response = await self.test_client.get("""/api/users_async?source={"query":{"match":{"first_name":"John"}}}""")
        json_data = await response.get_json()
        self.assertEqual(json_data["_meta"]["total"], 1)
        self.assertEqual(json_data["_items"], [test_user_dict])

        response = await self.test_client.get("""/api/users_async?source={"query":{"match":{"first_name":"James"}}}""")
        self.assertEqual((await response.get_json())["_meta"]["total"], 0)

    async def test_hateoas(self):
        # Test hateoas with empty resource
        response = await self.test_client.get("/api/users_async")
        json_data = await response.get_json()
        self.assertEqual(
            json_data["_meta"],
            {
                "max_results": 25,
                "page": 1,
                "total": 0,
            },
        )
        self.assertEqual(
            json_data["_links"],
            {
                "parent": {
                    "href": "/",
                    "title": "home",
                },
                "self": {
                    "href": "api/users_async",
                    "title": "users_async",
                },
                "next": {
                    "href": "api/users_async?max_results=25&page=2",
                    "title": "next page",
                },
            },
        )

        # Now add a user, and make sure hateoas & links are reflected
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        assert response.status_code == 201

        response = await self.test_client.get("/api/users_async")
        json_data = await response.get_json()
        self.assertEqual(
            json_data["_meta"],
            {
                "max_results": 25,
                "page": 1,
                "total": 1,
            },
        )
        self.assertEqual(
            json_data["_links"],
            {
                "parent": {
                    "href": "/",
                    "title": "home",
                },
                "self": {
                    "href": "api/users_async?max_results=25",
                    "title": "users_async",
                },
                "next": {
                    "href": "api/users_async?max_results=25&page=2",
                    "title": "next page",
                },
                "last": {
                    "href": "api/users_async?max_results=25",
                    "title": "last page",
                },
            },
        )

    async def test_aggregations(self):
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        assert response.status_code == 201

        # Test aggregations
        response = await self.test_client.get(
            """/api/users_async?source={"aggs":{"codes":{"terms":{"field":"code"}}}}"""
        )
        assert response.status_code == 200
        assert (await response.get_json())["_aggregations"]["codes"]["buckets"] == [{"doc_count": 1, "key": "my codes"}]

    async def test_post_validation(self):
        # Empty body
        response = await self.test_client.post("/api/users_async", json={})
        assert response.status_code == 403
        assert (await response.get_json()) == {
            "_status": "ERR",
            "_error": {"code": 403, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
            "_issues": {
                "first_name": {"required": "Field is required"},
                "last_name": {"required": "Field is required"},
            },
        }

        # Invalid data types
        response = await self.test_client.post(
            "/api/users_async",
            json={
                "first_name": "Monkey",
                "last_name": "Bar",
                "email": "incorrect email",
            },
        )
        assert response.status_code == 403
        assert (await response.get_json()) == {
            "_status": "ERR",
            "_error": {"code": 403, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
            "_issues": {
                "email": {"email": "Invalid email address"},
            },
        }

        # Valid request
        response = await self.test_client.post(
            "/api/users_async",
            json={
                "first_name": "Monkey",
                "last_name": "Bar",
            },
        )
        assert response.status_code == 201

    async def test_patch_validation(self):
        # Test item not found
        response = await self.test_client.patch("/api/users_async/abcd123", json={})
        assert response.status_code == 404

        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        assert response.status_code == 201

        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={"email": "incorrect email"},
        )
        assert response.status_code == 403
        assert (await response.get_json()) == {
            "_status": "ERR",
            "_error": {"code": 403, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
            "_issues": {
                "email": {"email": "Invalid email address"},
            },
        }

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_endpoint(self, mock_utcnow):
        # Populate the users resource
        test_user = john_doe()
        test_user_dict = self.test_client.model_instance_to_json(test_user)
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "Z",
                _updated=format_time(NOW) + "Z",
            )
        )

        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        # Use the custom endpoint to get the resource
        response = await self.test_client.get(f"/api/test_simple_route/{test_user.id}?resource=users_async")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), test_user_dict)

        # Use another custom endpoint to get all user IDs
        response = await self.test_client.get("/api/get_user_ids")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"ids": ["user_1"]})

        response = await self.test_client.get("/api/hello/world")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"hello": "world"})

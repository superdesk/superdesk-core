from copy import deepcopy
from typing import Any
from unittest import mock
import simplejson as json

from superdesk.utc import utcnow
from superdesk.utils import format_time

from superdesk.tests import AsyncFlaskTestCase, setup_auth_user, test_user

from .modules.users import UserResourceService
from .fixtures.users import john_doe, jane_doe


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
        post_response_data = await response.get_json()

        # Test the User exists in MongoDB with correct data
        test_user.created = NOW
        test_user.updated = NOW
        test_user_dict = test_user.to_dict(context={"use_objectid": True})
        mongo_item = await self.service.mongo_async.find_one({"_id": test_user.id})
        test_user.etag = test_user_dict["_etag"] = mongo_item["_etag"]
        self.assertEqual(mongo_item, test_user_dict)

        # Test the User exists in Elasticsearch with correct data
        # (Convert the datetime values to strings, as es client doesn't convert them)
        elastic_item = await self.service.elastic.find_by_id(test_user.id)
        test_user_dict = test_user.to_dict()
        # test_user_dict["_etag"] = mongo_item["_etag"]
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
            )
        )
        self.assertEqual(elastic_item, test_user_dict)

        # Test the POST response contains the correct etag
        self.assertDictContains(
            post_response_data,
            dict(
                _id=test_user.id,
                _etag=test_user.etag,
            ),
        )

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_get_item(self, mock_utcnow):
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        response = await self.test_client.get(f"/api/users_async/{test_user.id}")
        json_data = await response.get_json()
        test_user_dict = self.test_client.model_instance_to_json(test_user)
        test_user_dict.update(
            dict(_created=format_time(NOW) + "+00:00", _updated=format_time(NOW) + "+00:00", _etag=json_data["_etag"])
        )
        self.assertEqual(json_data, test_user_dict)

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_patch(self, mock_utcnow):
        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)

        original_etag = await self.get_resource_etag("users_async", test_user.id)
        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={
                "first_name": "Foo",
                "last_name": "Bar",
            },
            headers={"If-Match": original_etag},
        )
        self.assertEqual(response.status_code, 200)
        patch_response_data = await response.get_json()

        response = await self.test_client.get(f"/api/users_async/{test_user.id}")
        json_data = await response.get_json()
        test_user_dict = self.test_client.model_instance_to_json(test_user)
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
                _etag=json_data["_etag"],
                first_name="Foo",
                last_name="Bar",
            )
        )
        self.assertEqual(json_data, test_user_dict)
        self.assertDictContains(
            patch_response_data,
            dict(
                _id=test_user.id,
                _etag=json_data["_etag"],
                _updated=format_time(NOW) + "+0000",
                first_name="Foo",
                last_name="Bar",
            ),
        )

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
        json_data = await response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_data["_meta"]["total"], 1)

        # Test preconditionRequiredError/428 error is raised if etag not provided
        response = await self.test_client.delete(f"/api/users_async/{test_user.id}")
        self.assertEqual(response.status_code, 428)

        # Test preconditionFailedError/412 error is raised if etag is incorrect
        response = await self.test_client.delete(
            f"/api/users_async/{test_user.id}",
            headers={"If-Match": "my_etag_123"},
        )
        self.assertEqual(response.status_code, 412)

        # Delete the user, and make sure search is empty
        response = await self.test_client.delete(
            f"/api/users_async/{test_user.id}",
            headers={"If-Match": json_data["_items"][0]["_etag"]},
        )
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
        test_user_dict["_etag"] = json_data["_items"][0]["_etag"]
        self.assertEqual(json_data["_meta"]["total"], 1)
        self.assertEqual(json_data["_items"], [test_user_dict])

        response = await self.test_client.get("""/api/users_async?source={"query":{"match":{"first_name":"James"}}}""")
        self.assertEqual((await response.get_json())["_meta"]["total"], 0)

    async def test_hateoas(self):
        # Test hateoas with empty resource
        response = await self.test_client.get("/api/users_async")
        self.assertEqual(response.status_code, 200)
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
                    "title": "User",
                },
            },
        )

        # Now add 2 users, and make sure hateoas & links are reflected
        response = await self.test_client.post("/api/users_async", json=john_doe())
        assert response.status_code == 201
        response_json = await response.get_json()

        # Test the POST response contains HATEOAS link for self
        self_link = response_json["_links"]["self"]
        self.assertDictEqual(
            self_link,
            dict(
                title="User",
                href="users_async/user_1",
            ),
        )
        user_1_etag = response_json["_etag"]

        # Add the 2nd user
        response = await self.test_client.post("/api/users_async", json=jane_doe())
        assert response.status_code == 201

        response = await self.test_client.get("/api/users_async")
        json_data = await response.get_json()
        self.assertEqual(
            json_data["_meta"],
            {
                "max_results": 25,
                "page": 1,
                "total": 2,
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
                    "title": "User",
                },
            },
        )

        response = await self.test_client.get("/api/users_async?max_results=1")
        json_data = await response.get_json()
        self.assertEqual(
            json_data["_meta"],
            {
                "max_results": 1,
                "page": 1,
                "total": 2,
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
                    "href": "api/users_async?max_results=1",
                    "title": "User",
                },
                "next": {
                    "href": "api/users_async?max_results=1&page=2",
                    "title": "next page",
                },
                "last": {
                    "href": "api/users_async?max_results=1&page=2",
                    "title": "last page",
                },
            },
        )

        # Test the PATCH response contains HATEOAS link for self
        response = await self.test_client.patch(
            "/api/users_async/user_1", json={"first_name": "Foo"}, headers={"If-Match": user_1_etag}
        )
        response_json = await response.get_json()
        self.assertDictContains(
            response_json["_links"]["self"],
            dict(
                title="User",
                href="users_async/user_1",
            ),
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
        response = await self.test_client.patch("/api/users_async/abcd123", json={}, headers={"If-Match": "something"})
        assert response.status_code == 404

        test_user = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user)
        assert response.status_code == 201

        # Test preconditionRequiredError/428 error is raised if etag not provided
        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={"email": "incorrect email"},
        )
        assert response.status_code == 428

        # Test preconditionFailedError/412 error is raised if etag is incorrect
        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={"email": "incorrect email"},
            headers={"If-Match": "my_etag_123"},
        )
        assert response.status_code == 412

        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={"email": "incorrect email"},
            headers={"If-Match": await self.get_resource_etag("users_async", test_user.id)},
        )
        assert response.status_code == 403
        assert (await response.get_json()) == {
            "_status": "ERR",
            "_error": {"code": 403, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
            "_issues": {
                "email": {"email": "Invalid email address"},
            },
        }

        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={"email": "monkey@magic.org"},
            headers={"If-Match": await self.get_resource_etag("users_async", test_user.id)},
        )
        assert response.status_code == 200

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
        json_data = await response.get_json()
        test_user_dict["_etag"] = json_data["_etag"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_data, test_user_dict)

        # Use another custom endpoint to get all user IDs
        response = await self.test_client.get("/api/get_user_ids")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"ids": ["user_1"]})

        response = await self.test_client.get("/api/hello/world")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"hello": "world"})


class PrivilegedResourceEndpointsTestCase(AsyncFlaskTestCase):
    use_default_apps = True
    app_config = {
        "MODULES": [
            "tests.core.modules.users",
            "tests.core.modules.module_with_privileges",
        ]
    }

    async def _get_auth_token(self, user: dict[str, Any] | None = None):
        self.headers: list = []
        await setup_auth_user(self, user)

        auth_header = next((header for header in self.headers if header[0] == "Authorization"), None)
        if auth_header:
            return auth_header[1].replace("Basic", "Token")

        return ""

    async def _get_auth_header(self, user: dict[str, Any] | None = None) -> tuple:
        auth_token = await self._get_auth_token(user)
        return "Authorization", auth_token

    async def test_admin_can_access_privileged_endpoint(self):
        admin_user = deepcopy(test_user)
        admin_user["user_type"] = "administrator"

        headers = [await self._get_auth_header(admin_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)
        self.assertEqual(response.status_code, 200)

    async def test_unauthorized_user_cannot_access_privileged_endpoint(self):
        regular_user = deepcopy(test_user)
        regular_user["user_type"] = "unauthorized"

        headers = [await self._get_auth_header(regular_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)

        response_data = await response.get_json()
        self.assertEqual(response.status_code, 403)
        self.assertTrue("Insufficient privileges" in response_data["_message"])

    async def test_user_with_role_can_access_privileged_endpoint(self):
        from tests.core.modules.module_with_privileges import test_privileges

        can_read_privilege = test_privileges[0]
        roles = [{"name": "Can Read Role", "privileges": {can_read_privilege: 1}}]
        self.app.data.insert("roles", roles)

        regular_user = deepcopy(test_user)
        regular_user["user_type"] = "test_type"
        regular_user["role"] = roles[0]["_id"]

        headers = [await self._get_auth_header(regular_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)

        self.assertEqual(response.status_code, 200)

    async def test_cannot_access_endpoint_with_incorrect_privilege(self):
        from tests.core.modules.module_with_privileges import test_privileges

        can_create_privilege = test_privileges[1]
        can_create_only_role = {"name": "Can Read Role", "privileges": {can_create_privilege: 1}}
        self.app.data.insert("roles", [can_create_only_role])

        regular_user = deepcopy(test_user)
        regular_user["user_type"] = "test_type"
        regular_user["role"] = can_create_only_role["_id"]

        # user should not be able to "GET" as the role only has "POST" privilege
        headers = [await self._get_auth_header(regular_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)

        self.assertEqual(response.status_code, 403)

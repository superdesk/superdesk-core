from unittest import TestCase

from bson import ObjectId
from pydantic import ValidationError

from superdesk.core import json
from superdesk.core.types import SearchRequest, ProjectedFieldArg
from superdesk.core.resources import (
    ResourceModelWithObjectId,
    ResourceConfig,
    default_model_config,
    get_projection_from_request,
)
from superdesk.core.resources.utils import combine_projection_args, SYSTEM_FIELDS
from superdesk.tests import AsyncFlaskTestCase, AsyncTestCase
from superdesk.errors import SuperdeskApiError

from .modules.users import UserResourceService
from .fixtures.users import john_doe


class ResourceProjectionArgsTestCase(TestCase):
    def test_search_request_projection_arg(self):
        # Test empty args
        self.assertEqual(None, SearchRequest().projection)

        # Test json string loading
        self.assertEqual(None, SearchRequest(projection="").projection)
        self.assertEqual([], SearchRequest(projection="[]").projection)
        self.assertEqual(["name"], SearchRequest(projection='["name"]').projection)
        self.assertEqual({"name": True}, SearchRequest(projection='{"name": true}').projection)
        self.assertEqual({"name": 1}, SearchRequest(projection='{"name": 1}').projection)
        self.assertEqual({"name": False}, SearchRequest(projection='{"name": false}').projection)
        self.assertEqual({"name": 0}, SearchRequest(projection='{"name": 0}').projection)

        # Test invalid json
        with self.assertRaises(ValidationError):
            SearchRequest(projection="1?c")

    def test_combine_projection_arguments(self):
        self.assertEqual(None, combine_projection_args())
        self.assertEqual(None, combine_projection_args(None))
        self.assertEqual(None, combine_projection_args(SearchRequest()))
        self.assertEqual(None, combine_projection_args(SearchRequest(), SearchRequest()))

        # Test include fields - single value
        self.assertEqual({"name": True}, combine_projection_args(["name"]))
        self.assertEqual({"name": True}, combine_projection_args({"name": True}))
        self.assertEqual({"name": True}, combine_projection_args({"name": 1}))
        self.assertEqual({"name": True}, combine_projection_args(SearchRequest(projection=["name"])))
        self.assertEqual({"name": True}, combine_projection_args(SearchRequest(projection={"name": True})))
        self.assertEqual({"name": True}, combine_projection_args(SearchRequest(projection={"name": 1})))
        self.assertEqual({"name": True}, combine_projection_args(SearchRequest(args={"projections": '["name"]'})))
        self.assertEqual({"name": True}, combine_projection_args(SearchRequest(args={"projections": '{"name": true}'})))
        self.assertEqual({"name": True}, combine_projection_args(SearchRequest(args={"projections": '{"name": 1}'})))

        # Test exclude fields - single value
        expected_args = {"name": False}
        self.assertEqual(expected_args, combine_projection_args({"name": False}))
        self.assertEqual(expected_args, combine_projection_args({"name": 0}))
        self.assertEqual(expected_args, combine_projection_args(SearchRequest(projection={"name": False})))
        self.assertEqual(expected_args, combine_projection_args(SearchRequest(projection={"name": 0})))
        self.assertEqual(expected_args, combine_projection_args(SearchRequest(args={"projections": '{"name": false}'})))
        self.assertEqual(expected_args, combine_projection_args(SearchRequest(args={"projections": '{"name": 0}'})))

        # Test include fields - multiple values
        expected_args = {"name": True}
        self.assertEqual(expected_args, combine_projection_args(["name"], None))
        self.assertEqual(expected_args, combine_projection_args(["name"], ["name"]))
        self.assertEqual(expected_args, combine_projection_args(["name"], SearchRequest()))
        self.assertEqual(expected_args, combine_projection_args(["name"], {"password": False}))

        expected_args = {"name": True, "email": True}
        self.assertEqual(expected_args, combine_projection_args(["name"], {"email": True}))
        self.assertEqual(expected_args, combine_projection_args(["name"], SearchRequest(projection=["email"])))

        # Test exclude fields - multiple values
        expected_args = {"password": False, "token": False}
        self.assertEqual(expected_args, combine_projection_args({"password": False}, {"token": False}))
        self.assertEqual(
            expected_args, combine_projection_args({"password": False}, SearchRequest(projection={"token": False}))
        )

        # Test invalid projection - multiple values
        with self.assertRaises(SuperdeskApiError) as error:
            combine_projection_args({"password": False}, {"password": True})
        self.assertEqual(error.exception.status_code, 400)

        with self.assertRaises(SuperdeskApiError) as error:
            combine_projection_args({"destinations.config.secret_token": False}, {"destinations": True})
        self.assertEqual(error.exception.status_code, 400)


class ResourceFieldProjectionTestCase(AsyncFlaskTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}
    service: UserResourceService

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.async_app.elastic.init_index("users_async")
        self.service = UserResourceService()

    async def test_field_projection_from_search(self):
        response = await self.test_client.post("/api/users_async", json=john_doe())
        self.assertEqual(response.status_code, 201)

        async def assert_projection_result_keys(projection, expected_keys):
            # Test from mongo
            item = (await (await self.service.find({}, projection=projection, use_mongo=True)).to_list_raw())[0]
            self.assertListEqual(sorted(list(item.keys())), sorted(expected_keys))

            # Test from elasticsearch
            item = (await (await self.service.find({}, projection=projection, use_mongo=False)).to_list_raw())[0]
            self.assertListEqual(sorted(list(item.keys())), sorted(expected_keys))

            # Test from Web API
            projection_str = json.dumps(projection)
            url = "/api/users_async" if not projection else f"/api/users_async?projection={projection_str}"
            response = await self.test_client.get(url)
            item = (await response.get_json())["_items"][0]
            self.assertListEqual(sorted(list(item.keys())), sorted(expected_keys + ["_links"]))

        # Get baseline of keys to test against
        await assert_projection_result_keys(
            None,
            [
                "_created",
                "_etag",
                "_id",
                "_type",
                "_updated",
                "bio",
                "categories",
                "code",
                "email",
                "first_name",
                "last_name",
                "profile_id",
                "related_items",
            ],
        )
        await assert_projection_result_keys({"email": 1}, ["_etag", "_id", "_type", "email"])
        await assert_projection_result_keys({"email": True}, ["_etag", "_id", "_type", "email"])
        await assert_projection_result_keys(["email"], ["_etag", "_id", "_type", "email"])
        await assert_projection_result_keys(
            {"related_items": 0},
            [
                "_created",
                "_etag",
                "_id",
                "_type",
                "_updated",
                "bio",
                "categories",
                "code",
                "email",
                "first_name",
                "last_name",
                "profile_id",
            ],
        )
        await assert_projection_result_keys(
            {"related_items": False},
            [
                "_created",
                "_etag",
                "_id",
                "_type",
                "_updated",
                "bio",
                "categories",
                "code",
                "email",
                "first_name",
                "last_name",
                "profile_id",
            ],
        )

    async def test_projection_on_rest_only(self):
        user = john_doe()
        user.token = "abcd123"
        response = await self.test_client.post("/api/users_async", json=user)
        self.assertEqual(response.status_code, 201)

        # Test the token is not in the create response
        response_json = await response.get_json()
        self.assertEqual(response_json.get("token", None), None)

        # Test the item has token in the DB
        item = await self.service.find_by_id(user.id)
        self.assertEqual(item.token, "abcd123")

        # Test token is not in a get item response
        response = await self.test_client.get(f"/api/users_async/{user.id}")
        response_json = await response.get_json()
        self.assertEqual(response_json.get("token", None), None)

        # Test token is not in a search response
        response = await self.test_client.get("/api/users_async")
        response_json = await response.get_json()
        self.assertEqual(response_json["_items"][0]["_id"], user.id)
        self.assertEqual(response_json["_items"][0].get("token"), None)

        # Test token is not in an update response
        response = await self.test_client.patch(
            f"/api/users_async/{user.id}",
            json={"first_name": "Foo", "last_name": "Bar", "token": "9876zyxw"},
            headers={"If-Match": response_json["_items"][0]["_etag"]},
        )
        response_json = await response.get_json()
        self.assertEqual(response_json.get("token", None), None)

        item = await self.service.find_by_id(user.id)
        self.assertEqual(item.token, "9876zyxw")


class ResourceModelProjectionTestCase(AsyncTestCase):
    async def test_manual_registration(self):
        class User(ResourceModelWithObjectId):
            model_config = {
                **default_model_config,
                "extra": "forbid",
            }

            email: str
            is_enabled: bool

        class UserProfile(User):
            first_name: str | None = None
            last_name: str | None = None

        class UserAuth(User):
            password: str | None = None

        self.app.resources.register(
            ResourceConfig(
                name="user_profiles",
                datasource_name="users",
                data_class=UserProfile,
            )
        )
        self.app.resources.register(
            ResourceConfig(
                name="user_auth",
                datasource_name="users",
                data_class=UserAuth,
            )
        )
        user_profiles = self.app.resources.get_resource_service("user_profiles")
        user_auth = self.app.resources.get_resource_service("user_auth")

        # Create the User using the UserProfile resource
        new_user = (
            await user_profiles.create(
                [
                    UserProfile(
                        id=ObjectId(),
                        email="foo@bar.org",
                        first_name="Foo",
                        last_name="Bar",
                        is_enabled=True,
                    )
                ]
            )
        )[0]
        user_id = new_user.id

        # Assign a password using the UserAuth resource
        await user_auth.update(user_id, {"password": "some_hash"})

        # Retrieve the User from the UserProfile resource
        profile_item = (await user_profiles.find_by_id(user_id)).to_dict()
        self.assertIn("first_name", profile_item)
        self.assertIn("last_name", profile_item)
        self.assertNotIn("password", profile_item)

        # Retrieve the User from the UserAuth resource
        auth_item = (await user_auth.find_by_id(user_id)).to_dict()
        self.assertNotIn("first_name", auth_item)
        self.assertNotIn("last_name", auth_item)
        self.assertIn("password", auth_item)

        # Attempt to assign password using UserProfile resource
        with self.assertRaises(ValidationError):
            await user_profiles.update(user_id, {"password": "some_hash"})

        # Attempt to assign first/last names using UserAuth resource
        with self.assertRaises(ValidationError):
            await user_auth.update(user_id, {"first_name": "Monkey"})
        with self.assertRaises(ValidationError):
            await user_auth.update(user_id, {"first_name": "Magic"})

        await user_profiles.delete(await user_profiles.find_by_id(user_id))
        self.assertIsNone(await user_profiles.find_by_id(user_id))
        self.assertIsNone(await user_auth.find_by_id(user_id))

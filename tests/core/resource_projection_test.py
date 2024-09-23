from bson import ObjectId
from pydantic import ValidationError

from superdesk.core import json
from superdesk.core.resources import ResourceModelWithObjectId, ResourceConfig
from superdesk.tests import AsyncFlaskTestCase, AsyncTestCase

from .modules.users import UserResourceService
from .fixtures.users import john_doe


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
            self.assertListEqual(sorted(list(item.keys())), sorted(expected_keys))

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


class ResourceModelProjectionTestCase(AsyncTestCase):
    async def test_manual_registration(self):
        class User(ResourceModelWithObjectId):
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
        user_id = (
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

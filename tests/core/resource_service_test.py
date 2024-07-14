from unittest import mock

from pydantic import ValidationError
import simplejson as json

from superdesk.core.resources.cursor import SearchRequest
from superdesk.utc import utcnow
from superdesk.utils import format_time

from superdesk.tests.asyncio import AsyncTestCase

from .modules.users import UserResourceService
from .fixtures.users import test_users, john_doe


NOW = utcnow()


class ResourceServiceWithoutAppTestCase(AsyncTestCase):
    autorun = False

    def test_raises_runtimeerror(self):
        with self.assertRaises(RuntimeError):
            UserResourceService()


class TestResourceService(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}
    service: UserResourceService

    async def asyncSetUp(self):
        await super().asyncSetUp()
        print("TestResourceService.asyncSetUp")
        self.app.elastic.init_index("users")
        self.service = UserResourceService()

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_create(self, mock_utcnow):
        test_user = john_doe()

        # Create the new User
        await self.service.create([test_user])

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
    async def test_find_one(self, mock_utcnow):
        test_user = john_doe()
        await self.service.create([test_user])

        test_user.created = NOW
        test_user.updated = NOW
        item = await self.service.find_one(_id=test_user.id)
        self.assertEqual(test_user, item)

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_update(self, mock_utcnow):
        test_user = john_doe()
        await self.service.create([test_user])
        self.assertEqual(test_user, await self.service.find_by_id(test_user.id))

        await self.service.update(test_user.id, {"first_name": "Foo", "last_name": "Bar"})

        test_user.first_name = "Foo"
        test_user.last_name = "Bar"
        test_user.created = NOW
        test_user.updated = NOW
        test_user_dict = test_user.model_dump(by_alias=True, exclude_unset=True)

        # Test the user was updated through the ResourceService
        item = await self.service.find_one(_id=test_user.id)
        self.assertEqual(test_user, item)

        # Test the User was updated in MongoDB with correct data
        mongo_item = await self.service.mongo.find_one({"_id": test_user.id})
        self.assertEqual(mongo_item, test_user_dict)

        # Test the User was updated in Elasticsearch with correct data
        # (Convert the datetime values to strings, as es client doesn't convert them)
        elastic_item = await self.service.elastic.find_by_id(test_user.id)
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
            )
        )
        self.assertEqual(elastic_item, test_user_dict)

    async def test_update_validation(self):
        test_user = john_doe()
        await self.service.create([test_user])

        with self.assertRaises(ValidationError):
            await self.service.update(test_user.id, {"first_name": True})

        with self.assertRaises(ValidationError):
            await self.service.update(test_user.id, {"unknown_field": 1234})

    async def test_delete(self):
        # First create the user, and make sure it exists
        test_user = john_doe()
        await self.service.create([test_user])
        self.assertIsNotNone(await self.service.find_one(_id=test_user.id))

        # Now delete the user, and make sure it is gone from both MongoDB, Elastic
        # and the resource service
        await self.service.delete({"_id": test_user.id})
        self.assertIsNone(await self.service.mongo.find_one({"_id": test_user.id}))
        self.assertIsNone(await self.service.elastic.find_by_id(test_user.id))
        self.assertIsNone(await self.service.find_one(_id=test_user.id))

    async def test_get_all(self):
        users = test_users()
        item_ids = await self.service.create(users)
        self.assertEqual(item_ids, [user.id for user in users])
        docs = []
        async for user in self.service.get_all():
            docs.append(user)

        for i in range(3):
            self.assertEqual(
                docs[i].model_dump(by_alias=True, exclude_unset=True),
                users[i].model_dump(by_alias=True, exclude_unset=True),
            )

    async def test_get_all_batch(self):
        users = test_users()
        await self.service.create(users)

        docs = []
        async for user in self.service.get_all_batch():
            docs.append(user)

        self.assertEqual(len(docs), 3)
        for i in range(3):
            self.assertEqual(
                docs[i].model_dump(by_alias=True, exclude_unset=True),
                users[i].model_dump(by_alias=True, exclude_unset=True),
            )

        docs = []
        async for user in self.service.get_all_batch(size=1, max_iterations=2):
            docs.append(user)

        self.assertEqual(len(docs), 2)
        for i in range(2):
            self.assertEqual(
                docs[i].model_dump(by_alias=True, exclude_unset=True),
                users[i].model_dump(by_alias=True, exclude_unset=True),
            )

    async def test_elastic_search(self):
        users = test_users()
        await self.service.create(users)

        docs = []
        cursor = await self.service.search({})
        self.assertEqual(await cursor.count(), 3)
        async for user in cursor:
            docs.append(user)

        self.assertEqual(len(docs), 3)
        for i in range(3):
            print(f"doc={docs[i]}")
            print(f"user={users[i]}")
            self.assertEqual(docs[i], users[i])

        query = {"query": {"match": {"first_name": "John"}}}
        cursor = await self.service.search(query)
        self.assertEqual(await cursor.count(), 1)
        docs = []
        async for user in cursor:
            docs.append(user)
        self.assertEqual(len(docs), 1)
        self.assertEqual(users[0], docs[0])

        query = {"query": {"match": {"last_name": "Doe"}}}
        cursor = await self.service.search(query)
        self.assertEqual(await cursor.count(), 2)
        docs = []
        async for user in cursor:
            docs.append(user)
        self.assertEqual(len(docs), 2)
        self.assertEqual(users[0], docs[0])
        self.assertEqual(users[1], docs[1])

    async def test_mongo_search(self):
        users = test_users()
        await self.service.create(users)

        docs = []
        cursor = await self.service.search({}, use_mongo=True)
        self.assertEqual(await cursor.count(), 3)
        async for user in cursor:
            docs.append(user)

        self.assertEqual(len(docs), 3)
        for i in range(3):
            self.assertEqual(docs[i], users[i])

        query = {"first_name": "John"}
        cursor = await self.service.search(query, use_mongo=True)
        self.assertEqual(await cursor.count(), 1)
        docs = []
        async for user in cursor:
            docs.append(user)
        self.assertEqual(len(docs), 1)
        self.assertEqual(users[0], docs[0])

        query = {"last_name": "Doe"}
        cursor = await self.service.search(query, use_mongo=True)
        self.assertEqual(await cursor.count(), 2)
        docs = []
        async for user in cursor:
            docs.append(user)
        self.assertEqual(len(docs), 2)
        self.assertEqual(users[0], docs[0])
        self.assertEqual(users[1], docs[1])

    async def test_events(self):
        test_user = john_doe()
        self.service.on_create = mock.AsyncMock()
        self.service.on_created = mock.AsyncMock()
        await self.service.create([test_user])
        self.service.on_create.assert_called_once_with([test_user])
        self.service.on_created.assert_called_once_with([test_user])

        self.service.on_update = mock.AsyncMock()
        self.service.on_updated = mock.AsyncMock()
        updates = {"first_name": "Foo", "last_name": "Bar"}
        await self.service.update(test_user.id, updates)
        self.service.on_update.assert_called_once_with(test_user.id, updates, test_user)
        self.service.on_updated.assert_called_once_with(updates, test_user)

        self.service.on_delete = mock.AsyncMock()
        self.service.on_deleted = mock.AsyncMock()
        await self.service.delete(dict(_id=test_user.id))
        updated_test_user = test_user.model_copy(update=updates, deep=True)
        self.service.on_delete.assert_called_once_with(updated_test_user)
        self.service.on_deleted.assert_called_once_with(updated_test_user)

    async def test_elastic_find(self):
        users = test_users()
        await self.service.create(users)

        find_query = {
            "query": {
                "nested": {
                    "path": "related_items",
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"related_items.link_type": "text"}},
                                {"match": {"related_items.slugline": "sports-results"}},
                            ],
                        },
                    },
                },
            },
        }
        req = SearchRequest(args={"source": json.dumps(find_query)})
        cursor = await self.service.find(req)
        self.assertEqual(await cursor.count(), 2)

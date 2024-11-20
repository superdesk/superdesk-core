from unittest import mock

from pydantic import ValidationError
import simplejson as json
from bson import ObjectId

from superdesk.core.types import SearchRequest
from superdesk.core.resources import AsyncResourceService
from superdesk.core.elastic.base_client import ElasticCursor
from superdesk.utc import utcnow
from superdesk.utils import format_time

from superdesk.tests import AsyncTestCase


from .modules.users import UserResourceService, User
from .fixtures.users import all_users, john_doe, john_doe_dict


NOW = utcnow()


class ResourceServiceWithoutAppTestCase(AsyncTestCase):
    autorun = False

    def test_raises_runtimeerror(self):
        with self.assertRaises(RuntimeError):
            UserResourceService()


class TestResourceService(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}
    service: AsyncResourceService[User]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.elastic.init_index("users_async")
        self.service = User.get_service()

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_create(self, mock_utcnow):
        test_user = john_doe()

        # Create the new User
        await self.service.create([test_user])

        # Test the User exists in MongoDB with correct data
        test_user.created = NOW
        test_user.updated = NOW
        test_user_dict = test_user.to_dict(context={"use_objectid": True})
        mongo_item = await self.service.mongo_async.find_one({"_id": test_user.id})
        self.assertEqual(mongo_item, test_user_dict)

        # Check stored `_etag` vs generated one
        self.assertEqual(mongo_item.pop("_etag", None), self.service.generate_etag(mongo_item))

        # Make sure ObjectIds are not stored as strings
        self.assertTrue(isinstance(mongo_item["profile_id"], ObjectId))
        self.assertTrue(isinstance(mongo_item["related_items"][0]["_id"], ObjectId))
        self.assertTrue(isinstance(mongo_item["related_items"][1]["_id"], ObjectId))

        # Test the User exists in Elasticsearch with correct data
        # (Convert the datetime values to strings, as es client doesn't convert them)
        elastic_item = await self.service.elastic.find_by_id(test_user.id)
        test_user_dict = test_user.to_dict()
        test_user_dict.update(
            dict(
                _created=format_time(NOW) + "+00:00",
                _updated=format_time(NOW) + "+00:00",
            )
        )
        self.assertEqual(elastic_item, test_user_dict)

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_create_from_dict(self, mock_utcnow):
        test_user = john_doe_dict()

        # Create the new User
        await self.service.create([test_user])

        # Test the User exists in MongoDB with correct data
        test_user["created"] = NOW
        test_user["updated"] = NOW

        mongo_item = await self.service.find_by_id(test_user["_id"])
        self.assertIsNotNone(mongo_item)
        self.assertEqual(mongo_item.id, test_user["_id"])
        self.assertEqual(mongo_item.created, test_user["created"])
        self.assertEqual(mongo_item.updated, test_user["updated"])

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

        # Test passing in ObjectId as either an ObjectId instance of a  string
        # and making sure it's stored as ObjectId instance in MongoDB
        new_profile_id = str(ObjectId())
        new_related_item_1_id = str(ObjectId())
        new_related_item_2_id = ObjectId()
        updates = dict(
            first_name="Foo",
            last_name="Bar",
            profile_id=new_profile_id,
            related_items=[
                dict(
                    _id=new_related_item_1_id,
                    link_type=test_user.related_items[0].link_type,
                    slugline=test_user.related_items[0].slugline,
                ),
                dict(
                    _id=new_related_item_2_id,
                    link_type=test_user.related_items[1].link_type,
                    slugline=test_user.related_items[1].slugline,
                ),
            ],
        )
        await self.service.update(test_user.id, updates)

        test_user.first_name = "Foo"
        test_user.last_name = "Bar"
        test_user.created = NOW
        test_user.updated = NOW
        test_user.profile_id = new_profile_id
        test_user.related_items[0].id = new_related_item_1_id
        test_user.related_items[1].id = new_related_item_2_id
        test_user.etag = updates["_etag"]
        test_user_dict = test_user.to_dict(context={"use_objectid": True})

        # Test the user was updated through the ResourceService
        item = await self.service.find_one(_id=test_user.id)
        self.assertEqual(test_user, item)

        # Test the User was updated in MongoDB with correct data
        mongo_item = await self.service.mongo_async.find_one({"_id": test_user.id})
        self.assertEqual(mongo_item, test_user_dict)

        # Make sure ObjectIds are not stored as strings
        self.assertTrue(isinstance(mongo_item["profile_id"], ObjectId))
        self.assertTrue(isinstance(mongo_item["related_items"][0]["_id"], ObjectId))
        self.assertTrue(isinstance(mongo_item["related_items"][1]["_id"], ObjectId))

        # Test the User was updated in Elasticsearch with correct data
        # (Convert the datetime values to strings, as es client doesn't convert them)
        elastic_item = await self.service.elastic.find_by_id(test_user.id)
        test_user_dict = test_user.to_dict()
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
        await self.service.delete(test_user)
        self.assertIsNone(await self.service.mongo_async.find_one({"_id": test_user.id}))
        self.assertIsNone(await self.service.elastic.find_by_id(test_user.id))
        self.assertIsNone(await self.service.find_one(_id=test_user.id))

    async def test_delete_many(self):
        users = all_users()
        await self.service.create(users)
        self.assertEqual(await (await self.service.search({})).count(), 3)

        self.service.on_delete = mock.AsyncMock()
        self.service.on_deleted = mock.AsyncMock()
        await self.service.delete_many({"_id": {"$in": [users[0].id, users[1].id]}})
        self.assertEqual(await (await self.service.search({})).count(), 1)

        self.assertEqual(self.service.on_delete.call_count, 2)
        self.service.on_delete.assert_has_calls(
            [mock.call(users[0]), mock.call(users[1])],
            any_order=True,
        )
        self.service.on_deleted.assert_has_calls(
            [mock.call(users[0]), mock.call(users[1])],
            any_order=True,
        )

    async def test_get_all(self):
        users = all_users()
        item_ids = await self.service.create(users)
        self.assertEqual(item_ids, [user.id for user in users])
        docs = []
        async for user in self.service.get_all():
            docs.append(user)

        for i in range(3):
            self.assertEqual(
                docs[i].to_dict(),
                users[i].to_dict(),
            )

    async def test_get_all_batch(self):
        users = all_users()
        await self.service.create(users)

        docs = []
        async for user in self.service.get_all_batch():
            docs.append(user)

        self.assertEqual(len(docs), 3)
        for i in range(3):
            self.assertEqual(
                docs[i].to_dict(),
                users[i].to_dict(),
            )

        docs = []
        async for user in self.service.get_all_batch(size=1, max_iterations=2):
            docs.append(user)

        self.assertEqual(len(docs), 2)
        for i in range(2):
            self.assertEqual(
                docs[i].to_dict(),
                users[i].to_dict(),
            )

    async def test_elastic_search(self):
        users = all_users()
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
        users = all_users()
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
        self.service.on_update.assert_called_once_with(updates, test_user)
        self.service.on_updated.assert_called_once_with(updates, test_user)

        self.service.on_delete = mock.AsyncMock()
        self.service.on_deleted = mock.AsyncMock()
        updated_test_user = test_user.model_copy(update=updates, deep=True)
        await self.service.delete(updated_test_user)
        self.service.on_delete.assert_called_once_with(updated_test_user)
        self.service.on_deleted.assert_called_once_with(updated_test_user)

    async def test_elastic_find(self):
        users = all_users()
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

    async def test_sort_param(self):
        users = all_users()
        await self.service.create(users)

        items = await (await self.service.find({})).to_list()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].id, users[0].id)
        self.assertEqual(items[1].id, users[1].id)
        self.assertEqual(items[2].id, users[2].id)

        items = await (
            await self.service.find({}, sort=[("last_name.keyword", 1), ("first_name.keyword", 1)])
        ).to_list_raw()
        self.assertEqual(len(items), 3)
        self.assertDictContains(items[0], dict(first_name="Foo", last_name="Bar"))
        self.assertDictContains(items[1], dict(first_name="Jane", last_name="Doe"))
        self.assertDictContains(items[2], dict(first_name="John", last_name="Doe"))

        items = await (
            await self.service.find({}, sort=[("last_name.keyword", -1), ("first_name.keyword", -1)])
        ).to_list_raw()
        self.assertEqual(len(items), 3)
        self.assertDictContains(items[0], dict(first_name="John", last_name="Doe"))
        self.assertDictContains(items[1], dict(first_name="Jane", last_name="Doe"))
        self.assertDictContains(items[2], dict(first_name="Foo", last_name="Bar"))

    async def test_find_overloads(self):
        await self.service.create(all_users())

        async def assert_es_find_called_with(*args, **kwargs):
            expected = kwargs.pop("expected")
            self.service.elastic.find = mock.AsyncMock(return_value=(ElasticCursor(), 0))
            await self.service.find(*args, **kwargs)
            self.service.elastic.find.assert_called_once_with(expected)

        # Test without any arguments
        await assert_es_find_called_with(
            SearchRequest(), expected=SearchRequest(where=None, page=1, max_results=25, sort=None)
        )
        expected = SearchRequest()
        await assert_es_find_called_with(SearchRequest(), expected=expected)
        expected.where = {}
        await assert_es_find_called_with({}, expected=expected)

        sort_query = [("last_name.keyword", 1), ("first_name.keyword", 1)]
        expected = SearchRequest(sort=sort_query)
        await assert_es_find_called_with(SearchRequest(sort=sort_query), expected=expected)
        expected.where = {}
        await assert_es_find_called_with({}, sort=sort_query, expected=expected)

        kwargs = dict(
            page=2,
            max_results=5,
            sort=sort_query,
        )
        expected = SearchRequest(**kwargs)
        await assert_es_find_called_with(SearchRequest(**kwargs), expected=expected)
        expected.where = {}
        await assert_es_find_called_with({}, **kwargs, expected=expected)

        # Test with default sort in the resource config
        sort_query = [("email.keyword", 1)]
        self.service.config.default_sort = sort_query
        expected = SearchRequest(sort=sort_query)
        await assert_es_find_called_with(SearchRequest(), expected=expected)
        expected.where = {}
        await assert_es_find_called_with({}, expected=expected)

        # Test passing in sort param with default sort configured
        custom_sort_query = [("scores", 1)]
        expected = SearchRequest(sort=custom_sort_query)
        await assert_es_find_called_with(SearchRequest(sort=custom_sort_query), expected=expected)
        expected.where = {}
        await assert_es_find_called_with({}, sort=custom_sort_query, expected=expected)

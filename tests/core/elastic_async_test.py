import simplejson as json

from superdesk.tests import AsyncTestCase
from superdesk.core.types import SearchRequest

from .modules.users import User
from .fixtures.users import john_doe


class ElasticAsyncClientTestCase(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}

    async def test_insert(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")
        test_user = john_doe()
        item_ids = await client.insert([test_user.to_dict()])
        self.assertEqual(item_ids, [test_user.id])
        response = await client.find_by_id(test_user.id)
        self.assertEqual(response, test_user.to_dict())

    async def test_count(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")
        self.assertEqual(await client.count(), 0)
        self.assertTrue(await client.is_empty())

        test_user = john_doe()
        await client.insert([test_user.to_dict()])
        self.assertEqual(await client.count(), 1)
        self.assertFalse(await client.is_empty())

    async def test_bulk_insert(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")
        count, errors = await client.bulk_insert(
            [
                User(id="user_1", first_name="John", last_name="Doe").to_dict(),
                User(id="user_2", first_name="Jane", last_name="Doe").to_dict(),
                User(id="user_3", first_name="Foo", last_name="Bar").to_dict(),
            ]
        )
        self.assertEqual(count, 3)
        self.assertEqual(errors, [])
        self.assertEqual(await client.count(), 3)

    async def test_update(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")

        test_user = john_doe()
        await client.insert([test_user.to_dict()])
        response = await client.update(test_user.id, dict(last_name="Monkeys"))

        self.assertEqual(response["result"], "updated")
        self.assertEqual(response["forced_refresh"], True)
        self.assertEqual(response["_id"], test_user.id)

        response = await client.find_by_id(test_user.id)
        self.assertEqual(response["last_name"], "Monkeys")

    async def test_replace(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")

        test_user = john_doe()
        await client.insert([test_user.to_dict()])
        response = await client.replace(
            test_user.id,
            User(id="user_1", first_name="Monkey", last_name="Bars").to_dict(),
        )
        self.assertEqual(response["result"], "updated")
        self.assertEqual(response["forced_refresh"], True)
        self.assertEqual(response["_id"], test_user.id)
        self.assertEqual(
            await client.find_by_id(test_user.id),
            dict(_id="user_1", first_name="Monkey", last_name="Bars", _type="users_async"),
        )

    async def test_remove(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")

        test_user = john_doe()
        await client.insert([test_user.to_dict()])
        self.assertEqual(await client.count(), 1)
        response = await client.remove(test_user.id)
        self.assertEqual(response["_id"], test_user.id)
        self.assertEqual(response["result"], "deleted")
        self.assertEqual(response["forced_refresh"], True)
        self.assertIsNone(await client.find_by_id(test_user.id))
        self.assertEqual(await client.count(), 0)

    async def test_search(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")

        test_user = john_doe()
        await client.insert([test_user.to_dict()])

        # Test search using nested query
        response = await client.search(
            {
                "query": {
                    "nested": {
                        "path": "categories",
                        "query": {
                            "bool": {
                                "must": [
                                    {"match": {"categories.scheme": "sports"}},
                                    {"match": {"categories.qcode": "swimming"}},
                                ],
                            },
                        },
                    },
                },
            },
        )
        self.assertEqual(response["hits"]["hits"][0]["_id"], "user_1")

        response = await client.search(
            {
                "query": {
                    "nested": {
                        "path": "related_items",
                        "query": {
                            "bool": {
                                "must": [
                                    {"match": {"related_items.link_type": "text"}},
                                    {"term": {"related_items.slugline": "sports-results2"}},
                                ],
                            },
                        },
                    },
                },
            },
        )
        self.assertEqual(len(response["hits"]["hits"]), 0)

    async def test_find_by_id(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")

        test_user = john_doe()
        await client.insert([test_user.to_dict()])

        response = await client.find_by_id("user_1")
        self.assertEqual(response, test_user.to_dict())
        self.assertIsNone(await client.find_by_id("user_2"))

    async def test_find(self):
        self.app.elastic.init_index("users_async")
        client = self.app.elastic.get_client_async("users_async")

        # Test search using nested query
        test_user = john_doe()
        await client.insert([test_user.to_dict()])
        find_query = {
            "query": {
                "nested": {
                    "path": "categories",
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"categories.scheme": "sports"}},
                                {"match": {"categories.qcode": "swimming"}},
                            ],
                        },
                    },
                },
            },
        }
        req = SearchRequest(args={"source": json.dumps(find_query)})
        response, count = await client.find(req)
        self.assertEqual(count, 1)
        item = list(response)[0]
        self.assertEqual(item, test_user.to_dict())

        req.projection = ["first_name", "last_name"]
        response, count = await client.find(req)
        item = list(response)[0]
        self.assertEqual(sorted(list(item.keys())), ["_id", "_type", "first_name", "last_name"])

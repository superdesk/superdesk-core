import simplejson as json

from superdesk.tests.asyncio import AsyncTestCase
from superdesk.core.resources.fields import HTML, Keyword, ObjectId
from superdesk.core.elastic.common import SearchRequest

from .modules.users import User, RelatedItems, Category


test_user_1 = User(
    id="user_1",
    first_name="John",
    last_name="Doe",
    bio=HTML("<p>This is my bio</p>"),
    code=Keyword("my codes"),
    categories=[
        Category(qcode="sports", name="Sports", scheme="category"),
        Category(qcode="swimming", name="Swimming", scheme="sports"),
    ],
    related_items=[
        RelatedItems(id=ObjectId(), link_type=Keyword("text"), slugline=HTML("sports-results")),
        RelatedItems(id=ObjectId(), link_type=Keyword("photo"), slugline=HTML("sports-results")),
    ],
)


class ElasticClientTestCase(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}

    def test_insert(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        item_ids = client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])
        self.assertEqual(item_ids, [test_user_1.id])
        response = client.find_by_id(test_user_1.id)
        response.pop("_type")
        self.assertEqual(response, test_user_1.model_dump(by_alias=True, exclude_unset=True))

    def test_count(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        self.assertEqual(client.count(), 0)
        self.assertTrue(client.is_empty())

        client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])
        self.assertEqual(client.count(), 1)
        self.assertFalse(client.is_empty())

    def test_bulk_insert(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        count, errors = client.bulk_insert(
            [
                User(id="user_1", first_name="John", last_name="Doe").model_dump(by_alias=True, exclude_unset=True),
                User(id="user_2", first_name="Jane", last_name="Doe").model_dump(by_alias=True, exclude_unset=True),
                User(id="user_3", first_name="Foo", last_name="Bar").model_dump(by_alias=True, exclude_unset=True),
            ]
        )
        self.assertEqual(count, 3)
        self.assertEqual(errors, [])
        self.assertEqual(client.count(), 3)

    def test_update(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])
        response = client.update(test_user_1.id, dict(last_name="Monkeys"))

        self.assertEqual(response["result"], "updated")
        self.assertEqual(response["forced_refresh"], True)
        self.assertEqual(response["_id"], test_user_1.id)

        response = client.find_by_id(test_user_1.id)
        self.assertEqual(response["last_name"], "Monkeys")

    def test_replace(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])
        response = client.replace(
            test_user_1.id,
            User(id="user_1", first_name="Monkey", last_name="Bars").model_dump(by_alias=True, exclude_unset=True),
        )
        self.assertEqual(response["result"], "updated")
        self.assertEqual(response["forced_refresh"], True)
        self.assertEqual(response["_id"], test_user_1.id)
        self.assertEqual(
            client.find_by_id(test_user_1.id), dict(_id="user_1", first_name="Monkey", last_name="Bars", _type="users")
        )

    def test_remove(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])
        self.assertEqual(client.count(), 1)
        response = client.remove(test_user_1.id)
        self.assertEqual(response["_id"], test_user_1.id)
        self.assertEqual(response["result"], "deleted")
        self.assertEqual(response["forced_refresh"], True)
        self.assertIsNone(client.find_by_id(test_user_1.id))
        self.assertEqual(client.count(), 0)

    def test_search(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])

        # Test search using nested query
        response = client.search(
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

        response = client.search(
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

    def test_find_by_id(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")
        client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])

        response = client.find_by_id("user_1")
        response.pop("_type")
        self.assertEqual(response, test_user_1.model_dump(by_alias=True, exclude_unset=True))
        self.assertIsNone(client.find_by_id("user_2"))

    def test_find(self):
        self.app.elastic.init_index("users")
        client = self.app.elastic.get_client("users")

        # Test search using nested query
        client.insert([test_user_1.model_dump(by_alias=True, exclude_unset=True)])
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
        response, count = client.find(req)
        self.assertEqual(count, 1)
        item = list(response)[0]
        item.pop("_type")
        self.assertEqual(item, test_user_1.model_dump(by_alias=True, exclude_unset=True))

        req.projection = ["first_name", "last_name"]
        response, count = client.find(req)
        item = list(response)[0]
        item.pop("_type")
        self.assertEqual(sorted(list(item.keys())), ["_id", "first_name", "last_name"])

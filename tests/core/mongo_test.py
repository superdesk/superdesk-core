from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from superdesk.tests import AsyncTestCase
from .modules.users import user_model_config


class MongoClientTestCase(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}

    def test_mongo_resource_registration(self):
        assert self.app.mongo.get_resource_config("users_async") == user_model_config.mongo

        with self.assertRaises(KeyError):
            self.app.mongo.get_resource_config("profiles")

        # Test immutable resource config
        modified_resource_config = self.app.mongo.get_resource_config("users_async")
        modified_resource_config.prefix = "MONGO_MODIFIED"
        assert self.app.mongo.get_resource_config("users_async") != modified_resource_config

    def test_get_mongo_clients(self):
        client, db = self.app.mongo.get_client("users_async")
        assert isinstance(client, MongoClient)
        assert isinstance(db, Database)

        client, db = self.app.mongo.get_client_async("users_async")
        assert isinstance(client, AsyncIOMotorClient)
        assert isinstance(db, AsyncIOMotorDatabase)

    def test_collection_operations(self):
        collection = self.app.mongo.get_db("users_async").get_collection("users_async")

        assert collection.find_one({"_id": "user_1"}) is None

        collection.insert_one({"_id": "user_1", "name": "John"})
        assert collection.find_one({"_id": "user_1"})["name"] == "John"

        with self.assertRaises(DuplicateKeyError):
            collection.insert_one({"_id": "user_1", "name": "Bar"})

        collection.update_one({"_id": "user_1"}, {"$set": {"name": "Foo"}})
        assert collection.find_one({"_id": "user_1"})["name"] == "Foo"

        collection.delete_one({"_id": "user_1"})
        assert collection.find_one({"_id": "user_1"}) is None

    async def test_collection_operations_async(self):
        collection = self.app.mongo.get_db_async("users_async").get_collection("users_async")

        assert (await collection.find_one({"_id": "user_1"})) is None

        await collection.insert_one({"_id": "user_1", "name": "John"})
        assert (await collection.find_one({"_id": "user_1"}))["name"] == "John"

        with self.assertRaises(DuplicateKeyError):
            await collection.insert_one({"_id": "user_1", "name": "Bar"})

        await collection.update_one({"_id": "user_1"}, {"$set": {"name": "Foo"}})
        assert (await collection.find_one({"_id": "user_1"}))["name"] == "Foo"

        await collection.delete_one({"_id": "user_1"})
        assert (await collection.find_one({"_id": "user_1"})) is None

    def test_init_indexes(self):
        db = self.app.mongo.get_db("users_async")

        indexes = db.get_collection("users_async").index_information()
        self.assertIsNone(indexes.get("users_name_1"))
        self.assertIsNone(indexes.get("combined_name_1"))

        self.app.mongo.create_indexes_for_all_resources()
        indexes = db.get_collection("users_async").index_information()
        self.assertEqual(indexes["users_name_1"]["key"], [("first_name", 1)])
        self.assertEqual(indexes["users_name_1"]["unique"], True)
        self.assertEqual(indexes["users_name_1"]["background"], True)
        self.assertEqual(indexes["users_name_1"]["sparse"], True)

        self.assertEqual(indexes["combined_name_1"]["key"], [("first_name", 1), ("last_name", -1)])
        self.assertNotEqual(indexes["combined_name_1"].get("unique"), True)
        self.assertEqual(indexes["combined_name_1"]["background"], False)
        self.assertEqual(indexes["combined_name_1"]["sparse"], False)
        # ``collation`` uses an ``bson.son.SON` instance, so use that for testing here
        self.assertEqual(indexes["combined_name_1"]["collation"].get("locale"), "en")
        self.assertEqual(indexes["combined_name_1"]["collation"].get("strength"), 1)

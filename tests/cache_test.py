import random
from time import sleep

from superdesk.cache import cache
from superdesk.tests import TestCase
from bson import ObjectId


class Foo:
    def __init__(self):
        self.test_calls = 0

    @cache(ttl=1, tags=("count",))
    def count_calls(self):
        self.test_calls += 1
        return self.test_calls

    @cache(ttl=1, tags=("random",))
    def random(self):
        return random.random()

    @cache(ttl=1)
    def identity(self, identity):
        return identity


foo = Foo()


class CacheTestCase(TestCase):
    def test_cache(self):
        self.assertEqual(1, foo.count_calls())
        self.assertEqual(1, foo.count_calls(), "not using cache")
        sleep(2)
        self.assertEqual(2, foo.count_calls(), "expired")
        cache.clean()
        self.assertEqual(3, foo.count_calls(), "force expire")

        ran = foo.random()
        self.assertEqual(ran, foo.random())
        cache.clean(["random"])
        self.assertNotEqual(ran, foo.random())
        self.assertEqual(3, foo.count_calls())

    def test_cache_json_serializing(self):
        _id = ObjectId()
        self.assertEqual(_id, foo.identity(_id))
        self.assertNotEqual(_id, foo.identity(ObjectId()))
        self.assertEqual(_id, foo.identity(_id))

    def test_cache_cursor(self):
        self.app.data.insert("users", [{"username": "foo"}])

        @cache(ttl=5)
        def get_users():
            return [user for user in self.app.data.find_all("users")]

        users = get_users()
        self.assertEqual(users, get_users())

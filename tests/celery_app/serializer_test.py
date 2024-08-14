from bson import ObjectId
from datetime import datetime
from unittest.mock import MagicMock

from superdesk.celery_app.serializer import ContextAwareSerializerFactory
from superdesk.tests import TestCase, markers


@markers.requires_async_celery
class TestContextAwareSerializerFactory(TestCase):
    def setUp(self):
        self.get_current_app = MagicMock(return_value=self.app)
        self.factory = ContextAwareSerializerFactory(self.get_current_app)

    def test_try_cast_object_id(self):
        obj_id = ObjectId()
        result = self.factory.try_cast(str(obj_id))
        self.assertEqual(result, obj_id)

    def test_try_cast_datetime(self):
        date_str = "2021-09-10T14:31:09+0000"
        result = self.factory.try_cast(date_str)
        self.assertIsInstance(result, datetime)

    def test_dumps(self):
        obj = {"test": "data"}
        serialized = self.factory.dumps(obj)
        self.assertEqual(serialized, '{"test": "data"}')

    def test_serialize_dict(self):
        obj = {"key": "2021-09-10T14:31:09+0000", "nested": [{"_id": "528de7b03b80a13eefc5e610"}]}
        result = self.factory.serialize(obj)
        self.assertIsInstance(result["key"], datetime)
        self.assertIsInstance(result["nested"][0]["_id"], ObjectId)

    def test_serialize_list(self):
        obj = ["528de7b03b80a13eefc5e610", "2021-09-10T14:31:09+0000"]
        result = self.factory.serialize(obj)
        self.assertIsInstance(result[0], ObjectId)
        self.assertIsInstance(result[1], datetime)

    def test_loads_args(self):
        _id = "528de7b03b80a13eefc5e610"
        obj = b'{"args": [{"_id": "528de7b03b80a13eefc5e610", "_updated": "2014-09-10T14:31:09+0000"}]}'
        result = self.factory.loads(obj)
        self.assertEqual(result["args"][0]["_id"], ObjectId(_id))
        self.assertIsInstance(result["args"][0]["_updated"], datetime)

    def test_loads_kwargs(self):
        obj = b"""{"kwargs": "{}", "pid": 24998, "eta": null}"""
        result = self.factory.loads(obj)
        self.assertEqual({}, result["kwargs"])
        self.assertIsNone(result["eta"])

    def test_loads_lists(self):
        obj = b"""[{}, {"foo": null}]"""
        result = self.factory.loads(obj)
        self.assertEqual([{}, {"foo": None}], result)

    def test_loads_zero(self):
        obj = b"""[0]"""
        result = self.factory.loads(obj)
        self.assertEqual([0], result)

    def test_loads_boolean(self):
        obj = b"""[{"foo": false, "bar": true}]"""
        result = self.factory.loads(obj)
        self.assertEqual([{"foo": False, "bar": True}], result)

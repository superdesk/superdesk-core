from unittest import TestCase

from pydantic import ValidationError
from bson import ObjectId

from superdesk.core.resources import fields, ResourceModel, ResourceModelWithObjectId
from superdesk.core.elastic.resources import get_elastic_mapping_from_model

from .modules.users import User
from .fixtures.users import john_doe, profile_id, john_doe_dict


class ResourceModelTest(TestCase):
    def test_resource_model(self):
        test_user = john_doe()
        self.assertEqual(test_user.profile_id, profile_id)

        # Test converting model to dict, excluding unset values
        self.assertEqual(
            test_user.to_dict(),
            john_doe_dict(),
        )

        # Test ``code`` is now included
        test_user.code = "abcd"
        self.assertEqual(test_user.to_dict()["code"], "abcd")

        # Test assigning ``None`` to ``code` (aka nullable)
        test_user.code = None
        self.assertEqual(test_user.to_dict()["code"], None)

    def test_resource_from_dict(self):
        test_user_dict = john_doe_dict()
        user = User.model_validate(test_user_dict)
        self.assertEqual(user.to_dict(), test_user_dict)

    def test_resource_validation(self):
        with self.assertRaises(ValidationError):
            user = User()

        user = User(
            id="user_1",
            first_name="John",
            last_name="Doe",
            profile_id=profile_id,
            related_items=[],
            bio=fields.HTML("<p>This is my bio</p>"),
        )

        with self.assertRaises(ValidationError):
            user.location = fields.Geopoint(lat=30, lon="abcd")

        user.location = fields.Geopoint(lat=30, lon=30)
        with self.assertRaises(ValidationError):
            user.location.lat = "efgh"

    def test_resource_default_id(self):
        class ModelWithStringId(ResourceModel):
            name: str

        class ModelWithObjectId(ResourceModelWithObjectId):
            name: str

        self.assertIsInstance(ModelWithStringId(name="foo").id, str)
        self.assertIsInstance(ModelWithStringId(**{"name": "foo"}).id, str)
        self.assertIsInstance(ModelWithStringId.model_validate({"name": "foo"}).id, str)
        self.assertIsInstance(ModelWithStringId(id="abcd123", name="foo").id, str)

        self.assertIsInstance(ModelWithObjectId(name="foo").id, ObjectId)
        self.assertIsInstance(ModelWithObjectId(**{"name": "foo"}).id, ObjectId)
        self.assertIsInstance(ModelWithObjectId.model_validate({"name": "foo"}).id, ObjectId)
        self.assertIsInstance(ModelWithObjectId(id=ObjectId(), name="foo").id, ObjectId)

    def test_elastic_mapping(self):
        # Test the generated mapping
        self.assertEqual(
            get_elastic_mapping_from_model("users_async", User),
            {
                "properties": {
                    "_created": {"type": "date"},
                    "_updated": {"type": "date"},
                    "_etag": {"type": "text"},
                    "first_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "last_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "email": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "username": {"type": "text"},
                    "code": {"type": "keyword"},
                    "bio": {"type": "text", "analyzer": "html_field_analyzer"},
                    "categories": {
                        "type": "nested",
                        "properties": {
                            "qcode": {"type": "text"},
                            "name": {"type": "text"},
                            "scheme": {"type": "text"},
                        },
                    },
                    "profile_id": {"type": "text"},
                    "related_items": {
                        "type": "nested",
                        "properties": {
                            "_id": {"type": "text"},
                            "link_type": {"type": "keyword"},
                            "slugline": {"type": "text", "analyzer": "html_field_analyzer"},
                        },
                    },
                    "custom_field": {"type": "text", "analyzer": "html_field_analyzer"},
                    "score": {"type": "integer"},
                    "scores": {"type": "integer"},
                    "location": {"type": "geo_point"},
                    "my_dict": {"type": "object", "enabled": False},
                    "created_by": {"type": "text"},
                    "updated_by": {"type": "text"},
                },
            },
        )

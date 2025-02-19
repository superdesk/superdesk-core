from unittest import TestCase

from pydantic import ValidationError
from bson import ObjectId

from superdesk.core.resources import fields, ResourceModel, ResourceModelWithObjectId, dataclass, Dataclass
from superdesk.core.elastic.resources import get_elastic_mapping_from_model
from tests.core.modules.module_related_resources import RingOfPower

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
        user = User.from_dict(test_user_dict)
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
        self.assertIsInstance(ModelWithStringId.from_dict({"name": "foo"}).id, str)
        self.assertIsInstance(ModelWithStringId(id="abcd123", name="foo").id, str)

        self.assertIsInstance(ModelWithObjectId(name="foo").id, ObjectId)
        self.assertIsInstance(ModelWithObjectId(**{"name": "foo"}).id, ObjectId)
        self.assertIsInstance(ModelWithObjectId.from_dict({"name": "foo"}).id, ObjectId)
        self.assertIsInstance(ModelWithObjectId(id=ObjectId(), name="foo").id, ObjectId)

    def test_elastic_mapping(self):
        self.maxDiff = None
        # Test the generated mapping
        self.assertEqual(
            get_elastic_mapping_from_model("users_async", User),
            {
                "properties": {
                    "_created": {"type": "date"},
                    "_updated": {"type": "date"},
                    "_etag": {"type": "text"},
                    "first_name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                        "analyzer": "html_field_analyzer",
                    },
                    "last_name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                        "analyzer": "html_field_analyzer",
                    },
                    "email": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                        "analyzer": "html_field_analyzer",
                    },
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                        "analyzer": "html_field_analyzer",
                    },
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
                    "token": {"type": "text"},
                },
            },
        )

    def test_extra_fields(self):
        """Test serialising fields not defined in the ResourceModel"""

        @dataclass
        class Score(Dataclass):
            name: str
            score: int

        class Results(ResourceModel):
            model_resource_name = "Results"

            name: str
            scores: list[Score]

        score = dict(
            name="Maths",
            score=99,
            notes="Could do better",
        )
        data = dict(
            name="Foo",
            scores=[score],
            notes="Could focus more on maths.",
        )

        results = Results.from_dict(data)
        self.assertEqual(results.scores[0].to_dict(), score)
        results_dict = results.to_dict()
        self.assertEqual(results_dict["notes"], data["notes"])
        self.assertEqual(results_dict["scores"][0], score)

    def test_resource_model_class_relations(self):
        """Quickly tests that the relations are generated correctly"""
        self.assertEqual(len(User._related_field_definitions.keys()), 2)
        self.assertIn("created_by", User._related_field_definitions)
        self.assertIn("updated_by", User._related_field_definitions)

    def test_resource_model_class_calculates_inherited_relations(self):
        """Makes sure the relations are calculated taking into account parent's class relations"""
        self.assertEqual(len(RingOfPower._related_field_definitions.keys()), 2)

        # from parent class
        self.assertIn("bearer", RingOfPower._related_field_definitions)

        # current class
        self.assertIn("power", RingOfPower._related_field_definitions)

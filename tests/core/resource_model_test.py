from unittest import TestCase

from pydantic import ValidationError

from superdesk.core.resources import fields
from superdesk.core.elastic.resources import get_elastic_mapping_from_model

from .modules.users import User, RelatedItems, Category

profile_id = fields.ObjectId()
related_item1_id = fields.ObjectId()
related_item2_id = fields.ObjectId()
test_user = User(
    id="user_1",
    first_name="John",
    last_name="Doe",
    profile_id=profile_id,
    bio=fields.HTML("<p>This is my bio</p>"),
    categories=[
        Category(qcode="sports", name="Sports", scheme="category"),
        Category(qcode="swimming", name="Swimming", scheme="sports"),
    ],
    related_items=[
        RelatedItems(id=related_item1_id, link_type=fields.Keyword("text"), slugline=fields.HTML("sports-results")),
        RelatedItems(id=related_item2_id, link_type=fields.Keyword("photo"), slugline=fields.HTML("sports-results")),
    ],
)
test_user_dict = dict(
    _id="user_1",
    first_name="John",
    last_name="Doe",
    profile_id=str(profile_id),
    bio="<p>This is my bio</p>",
    categories=[
        dict(qcode="sports", name="Sports", scheme="category"),
        dict(qcode="swimming", name="Swimming", scheme="sports"),
    ],
    related_items=[
        dict(_id=str(related_item1_id), link_type="text", slugline="sports-results"),
        dict(_id=str(related_item2_id), link_type="photo", slugline="sports-results"),
    ],
)


class ResourceModelTest(TestCase):
    def test_resource_model(self):
        self.assertEqual(test_user.profile_id, profile_id)

        # Test converting model to dict, excluding unset values
        self.assertEqual(
            test_user.model_dump(exclude_unset=True, by_alias=True),
            test_user_dict,
        )

        # Test ``code`` is now included
        test_user.code = "abcd"
        self.assertEqual(test_user.model_dump(exclude_unset=True, by_alias=True)["code"], "abcd")

        # Test assigning ``None`` to ``code` (aka nullable)
        test_user.code = None
        self.assertEqual(test_user.model_dump(exclude_unset=True, by_alias=True)["code"], None)

    def test_resource_from_dict(self):
        user = User.model_validate(test_user_dict)

        self.assertEqual(user.model_dump(exclude_unset=True, by_alias=True), test_user_dict)

    def test_resource_validation(self):
        profile_id = fields.ObjectId()

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

    def test_elastic_mapping(self):
        # Test the generated mapping
        self.assertEqual(
            get_elastic_mapping_from_model("users", User),
            {
                "properties": {
                    "first_name": {"type": "text"},
                    "last_name": {"type": "text"},
                    "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
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
                    "score": {"type": "double"},
                    "location": {"type": "geo_point"},
                    "my_dict": {"type": "object", "enabled": False},
                },
            },
        )

from bson import ObjectId

from ..modules.users import User, RelatedItems, RelatedItemLinkType, Category

profile_id = ObjectId()
related_item1_id = ObjectId()
related_item2_id = ObjectId()


# pytest fixtures aren't supported in unittest classes,
# so we use standard functions and consume them within the test cases manually


def john_doe():
    return User(
        id="user_1",
        first_name="John",
        last_name="Doe",
        email="john@doe.org",
        profile_id=profile_id,
        bio="<p>This is my bio</p>",
        code="my codes",
        categories=[
            Category(qcode="sports", name="Sports", scheme="category"),
            Category(qcode="swimming", name="Swimming", scheme="sports"),
        ],
        related_items=[
            RelatedItems(id=related_item1_id, link_type=RelatedItemLinkType.text, slugline="sports-results"),
            RelatedItems(id=related_item2_id, link_type=RelatedItemLinkType.photo, slugline="sports-results"),
        ],
    )


def john_doe_dict():
    return dict(
        _id="user_1",
        _type="users_async",
        first_name="John",
        last_name="Doe",
        email="john@doe.org",
        profile_id=str(profile_id),
        bio="<p>This is my bio</p>",
        code="my codes",
        categories=[
            dict(qcode="sports", name="Sports", scheme="category"),
            dict(qcode="swimming", name="Swimming", scheme="sports"),
        ],
        related_items=[
            dict(_id=str(related_item1_id), link_type="text", slugline="sports-results"),
            dict(_id=str(related_item2_id), link_type="photo", slugline="sports-results"),
        ],
    )


def jane_doe():
    return User(
        id="user_2",
        first_name="Jane",
        last_name="Doe",
        email="jane@doe.org",
        related_items=[
            RelatedItems(id=ObjectId(), link_type=RelatedItemLinkType.text, slugline="sports-results"),
            RelatedItems(id=ObjectId(), link_type=RelatedItemLinkType.photo, slugline="sports-results"),
        ],
    )


def minimal_user():
    return User(id="user_3", first_name="Foo", last_name="Bar")


def test_users():
    return [
        john_doe(),
        jane_doe(),
        minimal_user(),
    ]

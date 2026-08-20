"""Desks, stages, users and archive items shared by the entity preview and Slack unfurl tests."""

from typing import Any

from bson import ObjectId

from superdesk.utc import utcnow


DESK_A = ObjectId("5d1f2c1f2c1f2c1f2c1f2c01")
DESK_B = ObjectId("5d1f2c1f2c1f2c1f2c1f2c02")
STAGE_A1 = ObjectId("5d1f2c1f2c1f2c1f2c1f2c11")
STAGE_A2 = ObjectId("5d1f2c1f2c1f2c1f2c1f2c12")
STAGE_B1 = ObjectId("5d1f2c1f2c1f2c1f2c1f2c13")

MEMBER_A = ObjectId("5d1f2c1f2c1f2c1f2c1f2c21")
OUTSIDER = ObjectId("5d1f2c1f2c1f2c1f2c1f2c22")
GLOBAL_VIEWER = ObjectId("5d1f2c1f2c1f2c1f2c1f2c23")
ADMIN = ObjectId("5d1f2c1f2c1f2c1f2c1f2c24")
DISABLED = ObjectId("5d1f2c1f2c1f2c1f2c1f2c25")
UNKNOWN = ObjectId("5d1f2c1f2c1f2c1f2c1f2c99")


def user(_id: ObjectId, username: str, **overrides) -> dict:
    doc = {
        "_id": _id,
        "username": username,
        "email": "{}@example.com".format(username),
        "user_type": "user",
        "is_active": True,
        "is_enabled": True,
        "privileges": {},
    }
    doc.update(overrides)
    return doc


def content_item(_id: str, creator: ObjectId, **overrides) -> dict:
    now = utcnow()
    doc = {
        "_id": _id,
        "guid": _id,
        "type": "text",
        "state": "in_progress",
        "headline": _id,
        "original_creator": creator,
        "version_creator": creator,
        "versioncreated": now,
        "_updated": now,
        "_created": now,
    }
    doc.update(overrides)
    return doc


def insert_content_fixtures(app: Any) -> None:
    """Two desks, one of them with an invisible stage, five users and a few archive items."""

    app.data.insert(
        "desks",
        [
            {"_id": DESK_A, "name": "Desk A", "members": [{"user": MEMBER_A}]},
            {"_id": DESK_B, "name": "Desk B", "members": []},
        ],
    )
    app.data.insert(
        "stages",
        [
            {"_id": STAGE_A1, "name": "A1", "desk": DESK_A, "is_visible": True},
            {"_id": STAGE_A2, "name": "A2", "desk": DESK_A, "is_visible": False},
            {"_id": STAGE_B1, "name": "B1", "desk": DESK_B, "is_visible": True},
        ],
    )
    app.data.insert(
        "users",
        [
            user(MEMBER_A, "member_a"),
            user(OUTSIDER, "outsider"),
            user(GLOBAL_VIEWER, "global_viewer", privileges={"use_global_saved_searches": 1}),
            user(ADMIN, "admin", user_type="administrator"),
            user(DISABLED, "disabled", is_enabled=False),
        ],
    )
    app.data.insert(
        "archive",
        [
            content_item("item_a1", ADMIN, task={"desk": DESK_A, "stage": STAGE_A1}),
            content_item("item_a2", ADMIN, task={"desk": DESK_A, "stage": STAGE_A2}),
            content_item("item_b1", ADMIN, task={"desk": DESK_B, "stage": STAGE_B1}),
            content_item("draft_b", ADMIN, state="draft", task={"desk": DESK_B, "stage": STAGE_B1}),
            content_item("personal_outsider", OUTSIDER, state="draft", task={"user": OUTSIDER}),
            content_item("personal_member", MEMBER_A, state="draft", task={"user": MEMBER_A}),
        ],
    )

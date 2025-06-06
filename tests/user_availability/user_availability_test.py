from bson import ObjectId
from datetime import datetime, date
from apps.user_availability import generate_user_availability


def test_user_availability_generator(app):
    active_user_id = ObjectId()
    inactive_user_id = ObjectId()

    app.data.insert(
        "users",
        [
            {"_id": active_user_id, "username": "active", "is_active": True},
            {"_id": inactive_user_id, "username": "inactive"},
        ],
    )
    app.data.insert(
        "default_user_availability",
        [
            {
                "_id": active_user_id,
                "language": ["en"],
                "tags": [
                    {"code": "tag1"},
                ],
                "working_days": {
                    "monday": {
                        "status": "available",
                        "working_hours": [],
                    },
                },
            },
            {
                "_id": inactive_user_id,
                "working_days": {
                    "friday": {"status": "available"},
                },
            },
        ],
    )

    generate_user_availability.apply()

    generated = list(app.data.find_all("user_availability"))
    assert len(generated) == 12
    generated_length = len(generated)

    for item in generated:
        if date.fromisoformat(item["date"]).weekday() == 0 and item["user"] == active_user_id:
            assert item["status"] == "available"
            assert item["language"] == ["en"]
            break
    else:
        raise AssertionError("Monday availability not found")

    generate_user_availability.apply()

    generated = list(app.data.find_all("user_availability"))
    assert len(generated) == generated_length

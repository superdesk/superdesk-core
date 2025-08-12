from bson import ObjectId
from datetime import date

from superdesk.tests import TestCase
from apps.user_availability import generate_user_availability


class UserAvailabilityTestCase(TestCase):
    async def test_user_availability_generator(self):
        active_user_id = ObjectId()
        inactive_user_id = ObjectId()

        self.app.data.insert(
            "users",
            [
                {"_id": active_user_id, "username": "active", "is_active": True},
                {"_id": inactive_user_id, "username": "inactive"},
            ],
        )
        self.app.data.insert(
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

        await generate_user_availability()

        generated = list(self.app.data.find_all("user_availability"))
        assert len(generated) == 12
        generated_length = len(generated)

        for item in generated:
            if date.fromisoformat(item["date"]).weekday() == 0 and item["user"] == active_user_id:
                assert item["status"] == "available"
                assert item["language"] == ["en"]
                break
        else:
            raise AssertionError("Monday availability not found")

        await generate_user_availability()

        generated = list(self.app.data.find_all("user_availability"))
        assert len(generated) == generated_length

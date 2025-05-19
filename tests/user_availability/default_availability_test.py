from bson import ObjectId
from datetime import date

from apps.user_availability.default_availability import default_service

TUESDAY = 1


def test_default_user_availability(app):
    user = ObjectId()

    default_availability = {
        "_id": user,
        "working_days": {
            "tuesday": {
                "status": "available",
                "tags": [{"code": "work"}],
            }
        },
        "language": ["en"],
    }

    default_service.generate_user_availability(default_availability)

    availability = list(app.data.find_all("user_availability"))
    for a in availability:
        assert date.fromisoformat(a["date"]).weekday() == TUESDAY
        assert a["status"] == "available"

from bson import ObjectId
from datetime import date, timedelta

from apps.user_availability.default_availability import default_service

TUESDAY = 1


def test_default_user_availability(app):
    user = ObjectId()
    today = date.today()

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

    future_monday = today + timedelta(days=7 + 7 - today.weekday())

    for a in availability:
        if a["date"] == future_monday.isoformat():
            break
    else:
        raise AssertionError("Future Monday availability not found")

    for a in availability:
        if date.fromisoformat(a["date"]).weekday() == TUESDAY:
            assert a["status"] == "available"
            break
    else:
        raise AssertionError("Tuesday availability not found")

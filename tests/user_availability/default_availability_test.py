from bson import ObjectId
from datetime import date, datetime
from unittest import mock

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


def test_default_user_availability_with_deleted_availability(app):
    user = ObjectId()
    user_availability = {"date": "2025-05-12", "status": "available", "user": user}
    app.data.insert("user_availability", [user_availability])
    assert user_availability["_id"]

    with app.test_client() as client:
        app.auth.authorized = mock.Mock(return_value=True)
        headers = {"If-Match": user_availability["_etag"]}
        resp = client.delete(f"/api/user_availability/{user_availability['_id']}", headers=headers)  # simulate deletion
        assert resp.status_code == 204

        resp = client.get("/api/user_availability")
        assert 200 == resp.status_code
        assert len(resp.json["_items"]) == 0

    default_availability = {
        "_id": user,
        "working_days": {
            "monday": {
                "status": "partial",
                "tags": [{"code": "work"}],
            }
        },
        "language": ["en"],
    }

    with mock.patch("apps.user_availability.default_availability.get_local_today", return_value=datetime(2025, 5, 5)):
        default_service.generate_user_availability(default_availability)

    availability = list(app.data.find_all("user_availability"))

    dates = set(a["date"] for a in availability)

    assert "2025-05-05" in dates
    assert "2025-05-12" not in dates
    assert "2025-05-19" in dates

import superdesk

from typing import TYPE_CHECKING
from flask import current_app as app
from datetime import timedelta
from dateutil.rrule import rrule, WEEKLY
from superdesk.dates import get_local_today
from superdesk.resource import Resource
from superdesk.errors import SuperdeskApiError
from apps.auth import get_user_id

if TYPE_CHECKING:
    from .availability import AvailabilityService

endpoint_name = "default_user_availability"


class DefaultAvailabilityResource(Resource):
    """Default user availability resource."""

    # Define a common day schema structure
    _day_schema = {
        "type": "dict",
        "schema": {
            "status": {
                "type": "string",
                "required": True,
                "allowed": ["available", "unavailable", "partial"],
            },
            "working_hours": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "start_time": {
                            "type": "string",
                            "nullable": True,
                        },
                        "end_time": {
                            "type": "string",
                            "nullable": True,
                        },
                        "tags": {
                            "type": "list",
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "code": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        },
    }

    schema = {
        # controls whether user has availability component enabled
        "enabled": {"type": "boolean"},
        "working_days": {
            "type": "dict",
            "schema": {
                "monday": _day_schema,
                "tuesday": _day_schema,
                "wednesday": _day_schema,
                "thursday": _day_schema,
                "friday": _day_schema,
                "saturday": _day_schema,
                "sunday": _day_schema,
            },
        },
        "language": {
            "type": "list",
            "schema": {"type": "string"},
            "required": False,
        },
        "tags": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "code": {"type": "string"},
                },
            },
        },
    }

    item_methods = ["GET", "PUT"]
    resource_methods = ["GET"]
    privileges = {"PUT": "users"}


class DefaultAvailabilityService(superdesk.Service):
    """Service class for the default user availability resource."""

    availability_service: "AvailabilityService"

    def on_replace(self, document, original):
        """Check that the user can only modify their own availability settings."""
        self.validate_user_id(document)

    def on_create(self, docs):
        for doc in docs:
            self.validate_user_id(doc)

    def validate_user_id(self, document):
        current_user_id = get_user_id()
        if str(document["_id"]) != str(current_user_id):
            raise SuperdeskApiError("You can only modify your own availability settings.", 403)

    def on_created(self, docs):
        """Event handler for created event."""
        for doc in docs:
            self.generate_user_availability(doc)

    def on_replaced(self, doc, original):
        """Event handler for replaced event."""
        if doc.get("working_days") != original.get("working_days") or doc.get("language") != original.get("language"):
            self.generate_user_availability(doc)

    def generate_all_users_availability(self):
        default_configs = self.get_all()
        users_service = superdesk.get_resource_service("users")
        for config in default_configs:
            user = users_service.find_one(req=None, _id=config["_id"])
            if not user or not user.get("is_active"):
                continue
            self.generate_user_availability(config)

    def generate_user_availability(self, doc):
        today = get_local_today().date()
        current_user_id = doc["_id"]
        generate_weeks = app.config.get("AVAILABILITY_GENERATE_WEEKS", 4 * 3)
        self.availability_service.delete_action(
            {"user": current_user_id, "date": {"$gte": today.isoformat()}, "_generated": True}
        )

        existing_availability_days = set(
            self.availability_service.get_user_set_availability_days(
                current_user_id, today, (today + timedelta(weeks=generate_weeks))
            )
        )
        working_days = doc.get("working_days") or {}

        items = []
        for day in working_days:
            weekday = WEEKDAY_RRULE_MAPPING[day]
            dates = rrule(freq=WEEKLY, dtstart=today, count=generate_weeks, byweekday=weekday)
            for d in dates:
                default_availability = working_days.get(day)
                if default_availability and d.date() not in existing_availability_days:
                    items.append(
                        {
                            "user": current_user_id,
                            "date": d.date().isoformat(),
                            "status": default_availability["status"],
                            "language": doc.get("language") or [],
                            "working_hours": default_availability["working_hours"]
                            if default_availability.get("working_hours")
                            else [],
                            "_generated": True,
                        }
                    )

        if items:
            sorted_items = sorted(items, key=lambda x: x["date"])
            self.availability_service.create(sorted_items)


default_service = DefaultAvailabilityService(endpoint_name, backend=superdesk.get_backend())


WEEKDAY_RRULE_MAPPING = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

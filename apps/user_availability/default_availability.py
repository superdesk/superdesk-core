import superdesk

from datetime import datetime
from dateutil.rrule import rrule, WEEKLY
from superdesk.resource import Resource
from superdesk.errors import SuperdeskApiError
from apps.auth import get_user_id


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
    }

    item_methods = ["GET", "PUT"]
    resource_methods = []
    privileges = {"PUT": "users"}


class DefaultAvailabilityService(superdesk.Service):
    """Service class for the default user availability resource."""

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
            self.regenerate_user_availability(doc)

    def on_replaced(self, doc, original):
        """Event handler for replaced event."""
        self.regenerate_user_availability(doc)

    def regenerate_user_availability(self, doc):
        today = datetime.now().date()
        current_user_id = get_user_id()
        availability_service = superdesk.get_resource_service("user_availability")
        availability_service.delete_action(
            {"user": current_user_id, "date": {"$gte": today.isoformat()}, "_generated": True}
        )
        generate_weeks = 4 * 3

        items = []
        for day in doc["working_days"]:
            weekday = WEEKDAY_RRULE_MAPPING[day]
            dates = rrule(freq=WEEKLY, dtstart=today, count=generate_weeks, byweekday=weekday)
            items += [
                {
                    "user": current_user_id,
                    "date": d.date().isoformat(),
                    "status": doc["working_days"][day]["status"],
                    "working_hours": doc["working_days"][day]["working_hours"]
                    if doc["working_days"][day].get("working_hours")
                    else [],
                    "_generated": True,
                }
                for d in dates
                if availability_service.find_one(req=None, user=current_user_id, date=d.date().isoformat()) is None
            ]

        if items:
            availability_service.create(items)


WEEKDAY_RRULE_MAPPING = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

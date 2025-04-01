import superdesk
from superdesk.resource import Resource
from superdesk.notification import push_notification
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
            push_notification("default_user_availability:created", item=str(doc.get("_id")))

    def on_updated(self, updates, original):
        """Event handler for updated event."""
        push_notification("default_user_availability:updated", item=str(original.get("_id")))

    def on_deleted(self, doc):
        """Event handler for deleted event."""
        push_notification("default_user_availability:deleted", item=str(doc.get("_id")))

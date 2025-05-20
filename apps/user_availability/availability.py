from typing import TYPE_CHECKING

import superdesk

from apps.user_availability.default_availability import DefaultAvailabilityService
from superdesk.resource import Resource
from apps.auth import get_user_id

from .privileges import validate_user_can_manage_availability

endpoint_name = "user_availability"

if TYPE_CHECKING:
    from .default_availability import DefaultAvailabilityService


class AvailabilityResource(Resource):
    """Resource for tracking user availability."""

    schema = {
        "user": Resource.rel("users"),
        "date": {
            "type": "string",
            "required": True,
        },
        "status": {
            "type": "string",
            "required": True,
            "allowed": ["available", "unavailable", "partial", "not-set"],
        },
        "language": {
            "type": "list",
            "schema": {"type": "string"},
            "required": False,
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
        "_generated": {
            "type": "boolean",
            "readonly": True,
        },
    }

    item_methods = ["GET", "PATCH", "PUT", "DELETE"]
    resource_methods = ["GET", "POST"]
    no_privileges = True
    mongo_indexes = {
        "date_user": ([("date", 1), ("user", 1)], {"unique": True}),
    }


class AvailabilityService(superdesk.Service):
    default_service: "DefaultAvailabilityService"

    def on_update(self, updates, original):
        validate_user_can_manage_availability(original["user"])
        assert "user" not in updates or updates["user"] == original["user"]
        updates["_generated"] = False

    def on_create(self, docs):
        for doc in docs:
            doc.setdefault("user", get_user_id())
            validate_user_can_manage_availability(doc["user"])
            default_availability = self.default_service.find_one(req=None, _id=doc["user"])
            if default_availability and default_availability.get("language"):
                doc.setdefault("language", default_availability["language"])

    def on_delete(self, doc):
        validate_user_can_manage_availability(doc["user"])


availability_service = AvailabilityService(endpoint_name, backend=superdesk.get_backend())

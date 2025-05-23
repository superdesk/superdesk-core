from typing import TYPE_CHECKING

import superdesk

from datetime import date
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
            "allowed": ["available", "unavailable", "partial"],
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
        "last_updated_by": Resource.rel("users"),
        "_generated": {
            "type": "boolean",
            "readonly": True,
        },
    }

    item_methods = ["GET", "PATCH", "PUT", "DELETE"]
    resource_methods = ["GET", "POST"]
    soft_delete = True
    no_privileges = True
    mongo_indexes = {
        "date_user": ([("date", 1), ("user", 1)], {"unique": True}),
    }


class AvailabilityService(superdesk.Service):
    default_service: "DefaultAvailabilityService"

    def on_update(self, updates, original):
        validate_user_can_manage_availability(original["user"])
        if "user" in updates and updates["user"] != original["user"]:
            raise ValueError("The 'user' field in updates must match the 'user' in the original data.")
        updates["_generated"] = False
        updates["last_updated_by"] = get_user_id()

    def on_create(self, docs):
        for doc in docs:
            doc.setdefault("user", get_user_id())
            validate_user_can_manage_availability(doc["user"])
            default_availability = self.default_service.find_one(req=None, _id=doc["user"])
            if default_availability and default_availability.get("language"):
                doc.setdefault("language", default_availability["language"])

            # delete deleted availability for the day before creating new one
            self.backend.get_mongo_collection(self.datasource).delete_one(
                {
                    "user": doc["user"],
                    "date": doc["date"],
                    "_deleted": True,
                }
            )
            doc["last_updated_by"] = get_user_id()

    def on_delete(self, doc):
        validate_user_can_manage_availability(doc["user"])

    def get_user_set_availability_days(self, user_id, from_date, to_date) -> list[date]:
        """
        Retrieve the days for which a user has availability records within a date range.

        Args:
            user_id (str): The ID of the user whose availability is being queried.
            from_date (date): The start date of the range (inclusive).
            to_date (date): The end date of the range (inclusive).

        Returns:
            list[date]: A list of `date` objects representing the days within the specified range
            for which the user has set availability. Excludes days marked as "_generated".
        """
        collection = self.backend.get_mongo_collection(self.datasource)
        return [
            date.fromisoformat(date_str)
            for date_str in collection.find(
                {
                    "user": user_id,
                    "date": {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()},
                }
            ).distinct("date")
        ]


availability_service = AvailabilityService(endpoint_name, backend=superdesk.get_backend())

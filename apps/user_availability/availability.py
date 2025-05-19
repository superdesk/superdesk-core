from typing import TYPE_CHECKING

import superdesk

from datetime import date
from apps.user_availability.default_availability import DefaultAvailabilityService
from superdesk.resource import Resource
from apps.auth import get_user_id

endpoint_name = "user_availability"

if TYPE_CHECKING:
    from .default_availability import DefaultAvailabilityService


class AvailabilityResource(Resource):
    """Resource for tracking user availability."""

    schema = {
        "user": Resource.rel("users", readonly=True),
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
        updates["_generated"] = False

    def on_create(self, docs):
        for doc in docs:
            doc["user"] = get_user_id()
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

    def get_user_set_availability_days(self, user_id, from_date, to_date) -> list[date]:
        """
        Retrieve the days for which a user has explicitly set availability within a date range.

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
            date.fromisoformat(doc["date"])
            for doc in collection.find(
                {
                    "user": user_id,
                    "date": {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()},
                    "_generated": {"$ne": True},
                }
            )
        ]


availability_service = AvailabilityService(endpoint_name, backend=superdesk.get_backend())

import superdesk
from superdesk.resource import Resource
from apps.auth import get_user_id

from . import endpoint_name


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
    no_privileges = True


class AvailabilityService(superdesk.Service):
    def on_create(self, docs):
        for doc in docs:
            doc["user"] = get_user_id()


availability_service = AvailabilityService(endpoint_name, backend=superdesk.get_backend())

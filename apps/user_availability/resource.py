from superdesk.resource import Resource


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
        "start_time": {
            "type": "string",
            "required": False,
            "nullable": True,
        },
        "end_time": {
            "type": "string",
            "required": False,
            "nullable": True,
        },
        "tags": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string"},
                    "code": {"type": "string"},
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

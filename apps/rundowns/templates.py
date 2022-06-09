import superdesk

from . import privileges


class TemplatesResource(superdesk.Resource):
    schema = {
        "name": {
            "type": "string",
            "required": True,
        },
        "show": superdesk.Resource.rel("rundown_shows", required=True),
        "description": {
            "type": "string",
        },
        "air_time": {
            "type": "string",
            "regex": r"[0-9]{2}:[0-9]{2}(:[0-9]{2})?$",
        },
        "duration": {
            "type": "number",
        },
        "schedule": {
            "type": "dict",
            "schema": {
                "is_active": {
                    "type": "boolean",
                },
                "day_of_week": {
                    "type": "list",
                    "allowed": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
                },
            },
        },
        "headline_template": {
            "type": "dict",
            "schema": {
                "prefix": {"type": "string"},
                "separator": {"type": "string"},
                "date_format": {"type": "string"},
            },
        },
        "created_by": superdesk.Resource.rel("users"),
        "updated_by": superdesk.Resource.rel("users"),
    }

    privileges = {"POST": privileges.RUNDOWNS, "PATCH": privileges.RUNDOWNS, "DELETE": privileges.RUNDOWNS}


class TemplatesService(superdesk.Service):
    pass

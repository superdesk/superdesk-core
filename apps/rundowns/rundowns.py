import superdesk

from . import privileges

from superdesk.metadata.item import metadata_schema


class RundownsResource(superdesk.Resource):
    resource_title = "Rundowns"
    schema = {
        "show": superdesk.Resource.rel("shows", required=True),
        "headline": metadata_schema["headline"],
        "rundown_template": superdesk.Resource.rel("rundown_templates"),
        "rundown_scheduled_on": {
            "type": "datetime",
            "readonly": True,
        },
        "duration": {
            "type": "number",
            "readonly": True,
        },
        "planned_duration": {
            "type": "number",
        },
        "airtime_time": {
            "type": "string",
        },
        "airtime_date": {
            "type": "string",
        },
        "airtime_datetime": {
            "type": "datetime",
        },
        "rundown_items": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "item": superdesk.Resource.rel("rundown_items", required=True),
                },
            },
        },
    }

    datasource = {
        "search_backend": "elastic",
    }

    versioning = True
    privileges = {"POST": privileges.RUNDOWNS, "PATCH": privileges.RUNDOWNS, "PUT": privileges.RUNDOWNS}

class RundownsService(superdesk.Service):
    pass
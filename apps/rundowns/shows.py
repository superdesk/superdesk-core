import superdesk

from . import privileges


class ShowsResource(superdesk.Resource):
    schema = {
        "name": {
            "type": "string",
            "required": True,
        },
        "description": {
            "type": "string",
        },
        "duration": {
            "type": "number",
        },
        "created_by": superdesk.Resource.rel("users"),
        "updated_by": superdesk.Resource.rel("users"),
    }

    privileges = {"POST": privileges.RUNDOWNS, "PATCH": privileges.RUNDOWNS, "DELETE": privileges.RUNDOWNS}


class ShowsService(superdesk.Service):
    pass

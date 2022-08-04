import superdesk

from . import privileges


class ShowsResource(superdesk.Resource):
    schema = {
        "title": {
            "type": "string",
            "required": True,
        },
        "description": {
            "type": "string",
        },
        "planned_duration": {
            "type": "number",
        },
        "created_by": superdesk.Resource.rel("users", readonly=True),
        "last_updated_by": superdesk.Resource.rel("users", readonly=True),
    }

    privileges = {"POST": privileges.RUNDOWNS, "PATCH": privileges.RUNDOWNS, "DELETE": privileges.RUNDOWNS}


class ShowsService(superdesk.Service):
    pass


shows_service = ShowsService()

import superdesk
import superdesk.utils as utils

from quart_babel import gettext

from . import privileges

from .templates import templates_service
from .rundowns import rundowns_service


class ShowsResource(superdesk.Resource):
    resource_title = "shows"

    schema = {
        "title": {
            "type": "string",
            "required": True,
        },
        "shortcode": superdesk.Resource.field("string"),
        "description": superdesk.Resource.field("string"),
        "planned_duration": {
            "type": "number",
        },
        "created_by": superdesk.Resource.rel("users", readonly=True),
        "last_updated_by": superdesk.Resource.rel("users", readonly=True),
    }

    privileges = {"POST": privileges.RUNDOWNS, "PATCH": privileges.RUNDOWNS, "DELETE": privileges.RUNDOWNS}


class ShowsService(superdesk.Service):
    def on_delete(self, doc):
        if rundowns_service.find_one(req=None, show=doc["_id"]) is not None:
            utils.abort(409, gettext("Can't remove show if there are rundowns."))
        return super().on_delete(doc)

    def on_deleted(self, doc):
        templates_service.delete_action({"show": doc["_id"]})
        return super().on_deleted(doc)


shows_service = ShowsService()

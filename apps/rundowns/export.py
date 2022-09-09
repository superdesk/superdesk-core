import superdesk

from bson import ObjectId
from flask import Blueprint, url_for, current_app as app, abort
from typing import List
from datetime import timezone, datetime, timedelta

from superdesk.utils import ListCursor, jwt_encode, jwt_decode

from . import privileges, rundowns, rundown_items, formatters, shows

EXPORT_EXPIRY_DAYS = 7

available_services: List[formatters.BaseFormatter] = []

blueprint = Blueprint("rundowns_export", __name__, url_prefix="/api")


@blueprint.route("/rundowns_export/<token>", methods=["GET"])
def export(token):
    payload = jwt_decode(token)
    if not payload:
        return abort(401)
    rundown = rundowns.rundowns_service.find_one(req=None, _id=ObjectId(payload["rundown"]))
    assert rundown is not None, {"rundown": 1}
    show = shows.shows_service.find_one(req=None, _id=rundown["show"])
    assert show is not None, {"show": 1}
    formatter = next((service for service in available_services if payload["format"] == service.id), None)
    assert formatter, {"formatter": 1}
    items = rundown_items.items_service.get_rundown_items(rundown)
    output, mimetype, filename = formatter.export(show, rundown, items)
    response = app.response_class(output, mimetype=mimetype)
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    with open(f"/tmp/rundowns-export-{filename}", "wb") as out:
        out.write(output)
    return response


class ExportResource(superdesk.Resource):
    schema = {
        "name": superdesk.Resource.field(type="string", readonly=True),
        "format": {
            "type": "string",
            "required": True,
        },
        "rundown": superdesk.Resource.rel("rundowns", required=True),
        "href": superdesk.Resource.field(type="string", readonly=True),
    }

    privileges = {
        "POST": privileges.RUNDOWNS,
    }


class ExportService(superdesk.Service):
    def get(self, req, lookup):
        return ListCursor(
            [
                dict(
                    _id=service.id,
                    name=service.name,
                )
                for service in available_services
            ]
        )

    def create(self, docs, **kwargs):
        return [self.set_link(doc) for doc in docs]

    def set_link(self, doc):
        doc["href"] = url_for(
            "rundowns_export.export",
            token=self.get_token(doc),
            _external=True,
            _scheme=app.config["PREFERRED_URL_SCHEME"],
        )
        return doc["rundown"]

    def get_token(self, doc):
        payload = {
            "format": doc["format"],
            "rundown": str(doc["rundown"]),
        }
        return jwt_encode(payload, expiry=EXPORT_EXPIRY_DAYS)


export_service = ExportService()

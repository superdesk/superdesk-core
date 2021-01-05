from flask import abort, request
from superdesk.resource import Resource
from superdesk.services import Service
from superdesk.metadata.utils import item_url
from superdesk.metadata.item import CONTENT_STATE
from .archive import ArchiveResource


ARCHIVE_DATASOURCE = ArchiveResource.datasource


def exclude_filter():
    if request:
        return {
            "bool": {
                "must_not": {
                    "term": {
                        "_id": request.view_args["item_id"],
                    }
                }
            }
        }


class ArchiveRelatedResource(Resource):
    endpoint_name = "archive_related"
    url = "archive/<{0}:item_id>/related".format(item_url)
    schema = {"lock_action": {"type": "string"}}
    datasource = {
        "source": "archive",
        "projection": ARCHIVE_DATASOURCE["projection"],
        "default_sort": ARCHIVE_DATASOURCE["default_sort"],
        "elastic_filter": {
            "bool": {
                "must": {
                    "terms": {
                        "state": [
                            CONTENT_STATE.INGESTED,
                            CONTENT_STATE.ROUTED,
                            CONTENT_STATE.FETCHED,
                            CONTENT_STATE.SUBMITTED,
                            CONTENT_STATE.PROGRESS,
                            CONTENT_STATE.PUBLISHED,
                            CONTENT_STATE.CORRECTED,
                            CONTENT_STATE.SCHEDULED,
                            CONTENT_STATE.KILLED,
                            CONTENT_STATE.RECALLED,
                            CONTENT_STATE.UNPUBLISHED,
                        ]
                    }
                },
            }
        },
        "elastic_filter_callback": exclude_filter,
    }
    resource_methods = ["GET"]
    item_methods = []
    resource_title = endpoint_name


class ArchiveRelatedService(Service):
    def get(self, req, lookup):
        item = self.find_one(req=req, _id=lookup["item_id"])
        if not item or not item.get("family_id"):
            abort(404)
        return super().get(req, {"family_id": item["family_id"]})

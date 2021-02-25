import superdesk

from flask import current_app as app
from apps.auth import is_current_user_admin


class ConfigResource(superdesk.Resource):
    schema = {
        "_id": {"type": "string", "required": True},
        "val": {"type": "dict", "schema": {}, "allow_unknown": True},
    }

    item_url = 'regex("[\w.:_-]+")'
    item_methods = ["GET"]
    resource_methods = ["POST"]


class ConfigService(superdesk.Service):
    def find_one(self, req, **lookup):
        item = super().find_one(req, **lookup)
        if item:
            return item
        else:
            return {"_id": lookup.get("_id"), "val": None}

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            self.set(doc["_id"], doc.get("val"))
            ids.append(doc["_id"])
        return ids

    def set(self, key, val, namespace="superdesk"):
        coll = app.data.mongo.get_collection_with_write_concern("config", "config")
        coll.update_one({"_id": key}, {"$set": {"_id": key, "val": val}}, upsert=True)

    def get(self, key, namespace="superdesk"):
        return self.find_one(req=None, _id=key).get("val")

    def is_authorizes(self, user):
        return is_current_user_admin()


def init_app(app) -> None:
    superdesk.register_resource("config", ConfigResource, ConfigService, _app=app)
    superdesk.intrinsic_privilege("config", method=["POST"])

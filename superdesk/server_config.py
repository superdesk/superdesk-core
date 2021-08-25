import superdesk

from flask import current_app as app
from apps.auth import is_current_user_admin
from pymongo.errors import DuplicateKeyError


class ConfigResource(superdesk.Resource):
    schema = {
        "_id": {"type": "string", "required": True},
        "val": {"type": "dict", "schema": {}, "allow_unknown": True},
    }

    item_url = 'regex("[\w.:_-]+")'
    item_methods = ["GET"]
    resource_methods = ["POST"]
    public_item_methods = ["GET"]


def get_default_value(key):
    return app.config["CONFIG_DEFAULTS"].get(key)


class ConfigService(superdesk.Service):
    def find_one(self, req, **lookup):
        item = super().find_one(req, **lookup)
        if item:
            return item
        else:
            return {"_id": lookup["_id"], "val": get_default_value(lookup["_id"])}

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            self.set(doc["_id"], doc.get("val"))
            ids.append(doc["_id"])
        return ids

    def set(self, key, val, namespace="superdesk"):
        coll = app.data.mongo.get_collection_with_write_concern("config", "config")
        default_value = get_default_value(key)
        if default_value:
            try:
                coll.insert_one({"_id": key, "val": default_value})
            except DuplicateKeyError:
                pass
        updates = {f"val.{k}": v for k, v in val.items()} if val else {}
        coll.update_one({"_id": key}, {"$set": dict(_id=key, **updates)}, upsert=True)

    def get(self, key, namespace="superdesk"):
        return self.find_one(req=None, _id=key).get("val")

    def is_authorizes(self, user):
        return is_current_user_admin()


def init_app(app) -> None:
    superdesk.register_resource("config", ConfigResource, ConfigService, _app=app)
    superdesk.intrinsic_privilege("config", method=["POST"])

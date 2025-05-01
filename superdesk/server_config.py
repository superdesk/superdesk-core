from motor.motor_asyncio import AsyncIOMotorCollection

import superdesk
from superdesk.eve_async import AsyncBaseService
from superdesk.core import get_current_app
from apps.auth import is_current_user_admin
from superdesk.utc import utcnow


class ConfigResource(superdesk.Resource):
    schema = {
        "_id": {"type": "string", "required": True},
        "val": {"type": "dict", "schema": {}, "allow_unknown": True},
        "init_version": {"type": "integer"},
    }

    item_url = 'regex("[\w.:_-]+")'
    item_methods = ["GET"]
    resource_methods = ["POST"]
    public_item_methods = ["GET"]


class ConfigService(AsyncBaseService):
    async def find_one_async(self, req, **lookup):
        item = await super().find_one_async(req, **lookup)
        if item:
            return item
        else:
            return {"_id": lookup["_id"], "val": None}

    async def create_async(self, docs, **kwargs):
        ids = []
        for doc in docs:
            await self.set(doc["_id"], doc.get("val"))
            ids.append(doc["_id"])
        return ids

    async def set(self, key, val, namespace="superdesk"):
        coll: AsyncIOMotorCollection = get_current_app().data.mongo_async.get_collection_with_write_concern(
            "config", "config"
        )
        if isinstance(val, dict):
            updates = {f"val.{k}": v for k, v in val.items()} if val else {}
        else:
            updates = {"val": val}
        updates["_updated"] = utcnow()
        await coll.update_one({"_id": key}, {"$set": dict(_id=key, **updates)}, upsert=True)

    async def get_async(self, key, namespace="superdesk"):
        return (await self.find_one_async(req=None, _id=key)).get("val")

    def is_authorizes(self, user):
        return is_current_user_admin()


def init_app(app) -> None:
    superdesk.register_resource("config", ConfigResource, ConfigService, _app=app)
    superdesk.intrinsic_privilege("config", method=["POST"])

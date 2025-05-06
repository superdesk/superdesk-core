"""Item Usage Metrics

Usage Metrics is endpoint used by client to store the metrics on user actions like open/preview.
It gets stored into its own collection with details like user and date, plus on the item
as numbers to be able to filter based on such actions::

    {"metrics": {
        "open": 2,
        "preview": 10
    }}

"""

from superdesk import get_resource_service, register_resource
from superdesk.resource import Resource, MongoIndexes
from superdesk.eve_async import AsyncBaseService


class UsageMetricsResource(Resource):
    no_privileges = True

    schema = {
        "action": {"type": "string", "required": True},
        "user": Resource.rel("users", required=True),
        "item": {"type": "string", "required": True},
        "date": {"type": "datetime"},
    }

    mongo_indexes: MongoIndexes = {
        "item_1": ([("item", 1)], {}),
    }

    url = "usage-metrics"
    item_methods = []
    notifications = False
    resource_methods = ["POST"]


class UsageMetricsService(AsyncBaseService):
    async def on_created_async(self, docs):
        for doc in docs:
            for resource in ["archive", "ingest"]:
                service = get_resource_service(resource)
                item = await service.find_one_async(req=None, _id=doc["item"])
                if not item:
                    continue
                await service.system_update_async(
                    item["_id"],
                    {"$inc": {f"metrics.{doc['action']}": 1}},
                    item,
                    change_request=True,
                    push_notification=False,
                )
        return await super().on_created_async(docs)


def init_app(_app) -> None:
    register_resource("usage_metrics", UsageMetricsResource, UsageMetricsService, _app=_app)

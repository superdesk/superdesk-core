"""Item Usage Metrics

Usage Metrics is endpoint used by client to store the metrics on user actions like open/preview.
It gets stored into its own collection with details like user and date, plus on the item
as numbers to be able to filter based on such actions::

    {"metrics": {
        "open": 2,
        "preview": 10
    }}

"""

import superdesk

from superdesk.resource import MongoIndexes


class UsageMetricsResource(superdesk.Resource):
    no_privileges = True

    schema = {
        "action": {"type": "string", "required": True},
        "user": superdesk.Resource.rel("users", required=True),
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


class UsageMetricsService(superdesk.Service):
    def on_created(self, docs):
        for doc in docs:
            archive_service = superdesk.get_resource_service("archive")
            item = archive_service.find_one(req=None, _id=doc["item"])
            archive_service.system_update(
                item["_id"],
                {"$inc": {f"metrics.{doc['action']}": 1}},
                item,
                change_request=True,
                push_notification=False,
            )
        return super().on_created(docs)


def init_app(_app) -> None:
    superdesk.register_resource("usage_metrics", UsageMetricsResource, UsageMetricsService, _app=_app)

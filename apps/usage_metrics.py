import superdesk


class UsageMetricsResource(superdesk.Resource):
    no_privileges = True

    schema = {
        "action": {"type": "string", "required": True},
        "user": superdesk.Resource.rel("users", required=True),
        "item": {"type": "string", "required": True},
        "date": {"type": "datetime"}
    }

    mongo_indexes = {
        "item_1": ([("item", 1)], {}),
    }

    url = "usage-metrics"
    item_methods = []
    resource_methods = ["POST"]


class UsageMetricsService(superdesk.Service):
    pass


def init_app(_app) -> None:
    superdesk.register_resource("usage_metrics", UsageMetricsResource, UsageMetricsService, _app=_app)
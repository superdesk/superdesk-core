import bson
import superdesk

from superdesk.dates import get_local_today


endpoint_name = "user_metrics"


class UserMetricsResource(superdesk.Resource):
    schema = {
        "user": superdesk.Resource.rel("users"),
        "date": {"type": "string"},
        "name": {"type": "string"},
        "value": {"type": "number"},
    }

    item_methods = []
    resource_methods = ["GET"]
    mongo_indexes = {
        "date_user_name_1": ([("date", 1), ("user", 1), ("name", 1)], {"unique": True}),
    }


class UserMetricsService(superdesk.Service):
    def incr(self, metric: str, user_id):
        """
        Increment the metric for the user.
        """
        lookup = {
            "user": user_id,
            "date": get_local_today().date().isoformat(),
            "name": metric,
        }

        updates = {
            "$inc": {
                "value": 1,
            }
        }

        self.find_and_modify(lookup, updates, upsert=True)


user_metrics_service = UserMetricsService(endpoint_name, backend=superdesk.get_backend())


def incr(metric: str, user_id: bson.ObjectId) -> None:
    """
    Increment the metric for the user.
    """
    user_metrics_service.incr(metric, user_id)

import superdesk

from datetime import timedelta
from superdesk.utc import utcnow
from superdesk.utils import get_random_token
from content_api import MONGO_PREFIX


class SubscriberTokenResource(superdesk.Resource):
    schema = {
        "_id": {"type": "string", "unique": True},
        "expiry": {"readonly": True},
        "expiry_days": {"type": "integer"},
        "subscriber": superdesk.Resource.rel("subscribers", required=True),
    }

    item_url = 'regex(".+")'
    resource_methods = ["GET", "POST"]
    item_methods = ["GET", "DELETE"]
    privileges = {"POST": "subscribers", "DELETE": "subscribers"}

    datasource = {
        "default_sort": [("_created", 1)],
    }

    mongo_prefix = MONGO_PREFIX


class SubscriberTokenService(superdesk.Service):
    def create(self, docs, **kwargs):
        for doc in docs:
            doc["_id"] = get_random_token()
            if doc.get("expiry_days"):
                doc.setdefault("expiry", utcnow() + timedelta(days=doc["expiry_days"]))
        return super().create(docs, **kwargs)

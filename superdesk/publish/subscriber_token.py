import superdesk
from pydantic import Field
from typing import Annotated
from datetime import timedelta, datetime

from content_api import MONGO_PREFIX
from superdesk.core.module import Module
from superdesk.utc import utcnow
from superdesk.utils import get_random_token
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules
from superdesk.core.resources import (
    ResourceModel,
    fields,
    AsyncResourceService,
    ResourceConfig,
    RestEndpointConfig,
)
from superdesk.core.resources.validators import validate_data_relation_async


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


class SubscriberToken(ResourceModel):
    id: Annotated[str, Field(alias="_id", default_factory=get_random_token)]
    expiry: datetime | None = None
    expiry_days: int | None = None
    subscriber: Annotated[fields.ObjectId, validate_data_relation_async("subscribers")]


class AsyncSubscriberTokenService(AsyncResourceService[SubscriberToken]):
    async def on_create(self, docs: list[SubscriberToken]) -> None:
        """
        Calculates and sets expiry dates based on expiry_days param.

        Args:
            docs: List of subscriber token models to be created
        """

        for doc in docs:
            if doc.expiry_days:
                doc.expiry = utcnow() + timedelta(days=doc.expiry_days)

        await super().on_create(docs)


resource_config = ResourceConfig(
    name="subscriber_token",
    data_class=SubscriberToken,
    service=AsyncSubscriberTokenService,
    default_sort=[("_created", 1)],
    rest_endpoints=RestEndpointConfig(
        resource_methods=["GET", "POST"],
        item_methods=["GET", "DELETE"],
        auth=http_method_privilege_based_rules(
            {
                "POST": "subscribers",
                "DELETE": "subscribers",
            }
        ),
        id_param_type="regex('.+')",
        populate_item_hateoas=True,
        enable_cors=True,
    ),
)


module = Module("superdesk.publish.subscriber_token", resources=[resource_config])

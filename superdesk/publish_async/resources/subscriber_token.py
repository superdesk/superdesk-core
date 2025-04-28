from datetime import timedelta

from superdesk.utc import utcnow
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules
from superdesk.core.resources import AsyncResourceService, ResourceConfig, RestEndpointConfig
from superdesk.types import SubscriberToken


class SubscriberTokenService(AsyncResourceService[SubscriberToken]):
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


subscriber_token_resource_config = ResourceConfig(
    name="subscriber_token",
    data_class=SubscriberToken,
    service=SubscriberTokenService,
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

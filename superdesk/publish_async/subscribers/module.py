from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules

from superdesk.types import SubscribersResource
from .service import SubscribersService
from .rest_api import SubscriberRestEndpoints


subscribers_resource_config = ResourceConfig(
    name="subscribers",
    data_class=SubscribersResource,
    service=SubscribersService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="name_1",
                keys=[("name", 1)],
                unique=True,
            )
        ]
    ),
    rest_endpoints=RestEndpointConfig(
        endpoints_class=SubscriberRestEndpoints,
        item_methods=["GET", "PATCH", "DELETE"],
        auth=http_method_privilege_based_rules(
            {
                "POST": "subscribers",
                "PATCH": "subscribers",
            }
        ),
    ),
)

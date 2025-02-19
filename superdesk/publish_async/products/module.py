from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules

from superdesk.types import ProductsResource
from .service import ProductsService


products_resource_config = ResourceConfig(
    name="products",
    data_class=ProductsResource,
    service=ProductsService,
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
        auth=http_method_privilege_based_rules(
            {
                "POST": "products",
                "PATCH": "products",
                "DELETE": "products",
            }
        )
    ),
)

from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules

from superdesk.types import ContentFiltersResource
from .service import ContentFiltersService
from .rest_api import ContentFilterRestEndpoints


content_filters_resource_config = ResourceConfig(
    name="content_filters",
    data_class=ContentFiltersResource,
    service=ContentFiltersService,
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
        endpoints_class=ContentFilterRestEndpoints,
        auth=http_method_privilege_based_rules(
            {
                "POST": "content_filters",
                "PATCH": "content_filters",
                "DELETE": "content_filters",
            }
        ),
    ),
)

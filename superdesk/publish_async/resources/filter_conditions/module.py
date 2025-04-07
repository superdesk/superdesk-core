from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules

from superdesk.types import FilterConditionsResource

from .service import FilterConditionsService


filter_conditions_resource_config = ResourceConfig(
    name="filter_conditions",
    data_class=FilterConditionsResource,
    service=FilterConditionsService,
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
                "POST": "content_filters",
                "PATCH": "content_filters",
                "DELETE": "content_filters",
            }
        )
    ),
)

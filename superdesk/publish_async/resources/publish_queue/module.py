from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules

from superdesk.types import PublishQueueResource
from .service import PublishQueueService


publish_queue_resource_config = ResourceConfig(
    name="publish_queue",
    data_class=PublishQueueResource,
    service=PublishQueueService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="subscriber_id_1",
                keys=[("subscriber_id", 1)],
                unique=False,
            )
        ]
    ),
    rest_endpoints=RestEndpointConfig(
        auth=http_method_privilege_based_rules(
            {
                "POST": "publish_queue",
                "PATCH": "publish_queue",
            }
        ),
        additional_lookup=dict(
            url=r'regex("[\w,.:-]+")',
            field="item_id",
        ),
    ),
    etag_ignore_fields=["moved_to_legal"],
    default_sort=[("_id", -1)],
)

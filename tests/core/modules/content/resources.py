from superdesk.core.resources import (
    ResourceConfig,
    RestEndpointConfig,
    AsyncResourceService,
    MongoResourceConfig,
    MongoIndexOptions,
    ElasticResourceConfig,
)
from .model import Content


class ContentResourceService(AsyncResourceService[Content]):
    resource_name = "content_async"


content_model_config = ResourceConfig(
    name="content_async",
    data_class=Content,
    service=ContentResourceService,
    versioning=True,
    ignore_fields_in_versions=["lock_user"],
    rest_endpoints=RestEndpointConfig(auth=False),
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="guid",
                keys=[("guid", 1)],
                background=True,
                unique=False,
            ),
        ],
        version_indexes=[
            MongoIndexOptions(
                name="uri_1",
                keys=[("uri", 1)],
                background=True,
                unique=False,
            )
        ],
    ),
)

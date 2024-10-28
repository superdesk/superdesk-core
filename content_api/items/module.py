from superdesk.core.module import Module
from superdesk.core.resources import (
    ResourceConfig,
    MongoResourceConfig,
    MongoIndexOptions,
    ElasticResourceConfig,
)
from content_api import MONGO_PREFIX, ELASTIC_PREFIX

from .model import ContentAPIItem
from .async_service import ContentAPIItemService


content_api_item_resource_config = ResourceConfig(
    name="items",
    data_class=ContentAPIItem,
    service=ContentAPIItemService,
    default_sort=[("versioncreated", -1)],
    versioning=True,
    mongo=MongoResourceConfig(
        prefix=MONGO_PREFIX,
        indexes=[
            MongoIndexOptions(
                name="_ancestors_",
                keys=[("ancestors", 1)],
            ),
            MongoIndexOptions(
                name="expiry_1",
                keys=[("expiry", 1)],
            ),
        ],
    ),
    elastic=ElasticResourceConfig(
        prefix=ELASTIC_PREFIX,
        filter={"bool": {"must_not": {"term": {"type": "composite"}}}},
    ),
    # TODO-ASYNC: Implement the GET & Search endpoints for this resource
)


module = Module(
    "content_api.items",
    resources=[content_api_item_resource_config],
)

from superdesk.core.mongo import MongoResourceConfig, MongoIndexOptions
from superdesk.core.elastic.resources import ElasticResourceConfig

from superdesk.core.resources import ResourceModelConfig
from superdesk.core.resources.service import AsyncResourceService
from superdesk.core.http.resource_endpoints import ResourceEndpoints


from .types import User


class UserResourceService(AsyncResourceService[User]):
    resource_name = "users_async"


user_model_config = ResourceModelConfig(
    name="users_async",
    data_class=User,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="users_name_1",
                keys=[("first_name", 1)],
            ),
            MongoIndexOptions(
                name="combined_name_1",
                keys=[("first_name", 1), ("last_name", -1)],
                background=False,
                unique=False,
                sparse=False,
                collation={"locale": "en", "strength": 1},
            ),
        ],
    ),
    elastic=ElasticResourceConfig(),
    service=UserResourceService,
)

users_resource_endpoints = ResourceEndpoints(
    user_model_config,
    resource_methods=["GET", "POST"],
    item_methods=["GET", "PATCH", "DELETE"],
)

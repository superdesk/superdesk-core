from superdesk.core.resources import (
    ResourceConfig,
    RestEndpointConfig,
    AsyncResourceService,
    MongoResourceConfig,
    MongoIndexOptions,
    ElasticResourceConfig,
)

from .types import User


class UserResourceService(AsyncResourceService[User]):
    resource_name = "users_async"


user_model_config = ResourceConfig(
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
    rest_endpoints=RestEndpointConfig(auth=False),
)

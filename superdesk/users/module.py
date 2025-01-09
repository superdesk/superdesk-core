from superdesk.core.resources import (
    ResourceConfig,
    MongoIndexOptions,
    MongoResourceConfig,
)
from superdesk.types import UsersResourceModel
from .async_service import UsersAsyncService


users_resource_config = ResourceConfig(
    name="users",
    data_class=UsersResourceModel,
    service=UsersAsyncService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="username_1",
                keys=[("username", 1)],
                unique=True,
            ),
            MongoIndexOptions(name="first_name_1_last_name_-1", keys=[("first_name", 1), ("last_name", -1)]),
        ]
    ),
)

from superdesk.core.module import Module
from .types import User, RelatedItems, RelatedItemLinkType, Category
from .resources import UserResourceService, user_model_config, users_resource_endpoints
from .endpoints import endpoints, hello_world

__all__ = [
    "UserResourceService",
    "User",
    "RelatedItems",
    "RelatedItemLinkType",
    "Category",
    "module",
]

module = Module(
    name="tests.users",
    resources=[user_model_config],
    http_endpoints=[
        users_resource_endpoints,
        endpoints,
        hello_world,
    ],
)

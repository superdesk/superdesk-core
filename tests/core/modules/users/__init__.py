from superdesk.core.module import Module
from .types import User, RelatedItems, RelatedItemLinkType, Category
from .resources import UserResourceService, user_model_config
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
    endpoints=[
        endpoints,
        hello_world,
    ],
)

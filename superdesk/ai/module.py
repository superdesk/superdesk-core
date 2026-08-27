from quart_babel import lazy_gettext as _

from superdesk.core.auth.privilege_rules import required_privilege_rule
from superdesk.core.module import Module
from superdesk.core.privileges import Privilege
from superdesk.core.resources import (
    MongoIndexOptions,
    MongoResourceConfig,
    ResourceConfig,
    RestEndpointConfig,
)

from .config import config
from .models import AIProvider
from .service import AIProvidersService

#: Grants access to the AI configuration: the providers and, later, the actions built on them
AI_STUDIO_PRIVILEGE = "ai_studio"

#: Grants the right to run AI actions on content
AI_PRIVILEGE = "ai"

ai_providers_config = ResourceConfig(
    name="ai_providers",
    data_class=AIProvider,
    service=AIProvidersService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="name_1", keys=[("name", 1)], unique=False),
        ]
    ),
    # Filtering by the key would let a client with read access confirm it one regex at a time
    sensitive_fields=["api_key"],
    rest_endpoints=RestEndpointConfig(
        resource_methods=["GET", "POST"],
        item_methods=["GET", "PATCH", "DELETE"],
        auth=[required_privilege_rule(AI_STUDIO_PRIVILEGE)],
        exclude_fields_in_response={"GET": ["api_key"], "POST": ["api_key"], "PATCH": ["api_key"]},
    ),
)

module = Module(
    name="superdesk.ai",
    resources=[ai_providers_config],
    config=config,
    config_prefix="AI",
    privileges=[
        Privilege(
            name=AI_STUDIO_PRIVILEGE,
            label=_("AI Studio"),
            description=_("Manage AI providers and actions"),
        ),
        Privilege(
            name=AI_PRIVILEGE,
            label=_("AI"),
            description=_("Use AI actions"),
        ),
    ],
)

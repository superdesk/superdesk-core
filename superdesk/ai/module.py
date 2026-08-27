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
from .models import AIAction, AIEvent, AIProvider
from .privileges import AI_PRIVILEGE, AI_STUDIO_PRIVILEGE
from .rest_endpoints import AIActionsEndpoints, AIProvidersEndpoints
from .service import AIActionsService, AIEventsService, AIProvidersService

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
        endpoints_class=AIProvidersEndpoints,
    ),
)

ai_actions_config = ResourceConfig(
    name="ai_actions",
    data_class=AIAction,
    service=AIActionsService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="provider_1", keys=[("provider", 1)], unique=False),
        ]
    ),
    rest_endpoints=RestEndpointConfig(
        resource_methods=["GET", "POST"],
        item_methods=["GET", "PATCH", "DELETE"],
        auth=[required_privilege_rule(AI_STUDIO_PRIVILEGE)],
        endpoints_class=AIActionsEndpoints,
    ),
)

ai_events_config = ResourceConfig(
    name="ai_events",
    data_class=AIEvent,
    service=AIEventsService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="item_id_1", keys=[("item_id", 1)], unique=False),
            MongoIndexOptions(name="action_id_1", keys=[("action_id", 1)], unique=False),
            MongoIndexOptions(name="user_id_1", keys=[("user_id", 1)], unique=False),
            MongoIndexOptions(name="requested_at_1", keys=[("requested_at", 1)], unique=False),
        ]
    ),
    rest_endpoints=RestEndpointConfig(
        # Entries are written by a run, never by a client, and never deleted through the API
        resource_methods=["GET"],
        item_methods=["GET"],
        auth=[required_privilege_rule(AI_STUDIO_PRIVILEGE)],
    ),
)

module = Module(
    name="superdesk.ai",
    resources=[ai_providers_config, ai_actions_config, ai_events_config],
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

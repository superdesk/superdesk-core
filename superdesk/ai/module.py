"""Configuration of the AI providers Superdesk talks to, and the actions built on top of them.

Security boundary: provider credentials are stored unencrypted, the way ingest and search provider
credentials are. The ``ai_studio`` privilege is therefore equivalent to access to every stored key.
A holder can point a provider's ``base_url`` at a host they control and have the key sent there,
and can narrow a key down by sorting a listing on ``api_key``, even though the key itself is never
returned in a response. Grant the privilege only to users already trusted with the system's
credentials.
"""

from quart_babel import lazy_gettext as _

from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules, required_privilege_rule
from superdesk.core.module import Module
from superdesk.core.privileges import Privilege
from superdesk.core.resources import (
    MongoIndexOptions,
    MongoResourceConfig,
    ResourceConfig,
    RestEndpointConfig,
)

from .actions_service import AIActionsService
from .config import config
from .events_service import AIEventsService
from .models import AIAction, AIEvent, AIProvider
from .privileges import AI_PRIVILEGE, AI_STUDIO_PRIVILEGE
from .providers_service import AIProvidersService
from .rest_endpoints import AIActionsEndpoints, AIEventsEndpoints, AIProvidersEndpoints

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
    # No concurrency risk: reporting an outcome is the only update and nothing races for it.
    uses_etag=False,
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
        item_methods=["GET", "PATCH"],
        # Reading the log is a configuration right, reporting what happened to a suggestion is part
        # of running actions, so the editor doing it needs nothing more than ``ai``. ``HEAD`` is
        # answered by the ``GET`` handler and a method these rules do not name keeps the login rule
        # alone, so it has to be listed next to ``GET`` rather than left out.
        auth=http_method_privilege_based_rules(
            {"GET": AI_STUDIO_PRIVILEGE, "HEAD": AI_STUDIO_PRIVILEGE, "PATCH": AI_PRIVILEGE}
        ),
        endpoints_class=AIEventsEndpoints,
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

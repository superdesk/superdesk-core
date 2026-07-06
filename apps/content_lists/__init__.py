from quart_babel import lazy_gettext as _

from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules
from superdesk.core.module import Module
from superdesk.core.privileges import Privilege
from superdesk.core.resources import (
    ResourceConfig,
    RestEndpointConfig,
    RestParentLink,
    MongoResourceConfig,
    MongoIndexOptions,
)

from .models import ContentList, ContentListItem, ContentListWebhook
from .service import ContentListsService, ContentListItemsService
from .rest_endpoints import ContentListItemsEndpoints
from .webhooks import ContentListWebhooksService


content_lists_config = ResourceConfig(
    name="content_lists",
    data_class=ContentList,
    service=ContentListsService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="name_1", keys=[("name", 1)], unique=False),
        ]
    ),
    rest_endpoints=RestEndpointConfig(
        resource_methods=["GET", "POST"],
        item_methods=["GET", "PATCH", "DELETE"],
    ),
)

content_list_items_config = ResourceConfig(
    name="content_list_items",
    data_class=ContentListItem,
    service=ContentListItemsService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="list_id_1", keys=[("list_id", 1)], unique=False),
            MongoIndexOptions(name="list_id_content_1", keys=[("list_id", 1), ("content", 1)], unique=True),
        ]
    ),
    rest_endpoints=RestEndpointConfig(
        url="items",
        resource_methods=["GET"],
        item_methods=["GET", "PATCH"],
        parent_links=[RestParentLink(resource_name="content_lists", model_id_field="list_id")],
        endpoints_class=ContentListItemsEndpoints,
    ),
)

content_list_webhooks_config = ResourceConfig(
    name="content_list_webhooks",
    data_class=ContentListWebhook,
    service=ContentListWebhooksService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="enabled_1", keys=[("enabled", 1)], unique=False),
        ]
    ),
    rest_endpoints=RestEndpointConfig(
        resource_methods=["GET", "POST"],
        item_methods=["GET", "PATCH", "DELETE"],
        auth=http_method_privilege_based_rules(
            {
                # GET included: webhook URLs may embed auth tokens, so reads
                # are limited to users who can manage content lists.
                "GET": "content_lists",
                "POST": "content_lists",
                "PATCH": "content_lists",
                "DELETE": "content_lists",
            }
        ),
    ),
)

module = Module(
    name="apps.content_lists",
    resources=[content_lists_config, content_list_items_config, content_list_webhooks_config],
    privileges=[Privilege(name="content_lists", label=_("Content Lists"), description=_("Manage content lists"))],
)

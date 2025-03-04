from quart_babel import lazy_gettext

from superdesk.core.module import Module
from superdesk.core.privileges import Privilege

from .content_filters.module import content_filters_resource_config
from .filter_conditions.module import filter_conditions_resource_config
from .products.module import products_resource_config
from .publish_queue.module import publish_queue_resource_config
from .sequences import sequences_resource_config
from .subscribers.module import subscribers_resource_config

from .commands import *  # noqa


module = Module(
    name="superdesk.publish_async",
    resources=[
        content_filters_resource_config,
        filter_conditions_resource_config,
        products_resource_config,
        publish_queue_resource_config,
        sequences_resource_config,
        subscribers_resource_config,
    ],
    privileges=[
        Privilege(
            name="content_filters",
            label=lazy_gettext("Content Filters"),
            description=lazy_gettext("User can manage content filters"),
        ),
        Privilege(
            name="products",
            label=lazy_gettext("Products Management"),
            description=lazy_gettext("User can manage product lists."),
        ),
        Privilege(
            name="publish_queue",
            label=lazy_gettext("Publish Queue"),
            description=lazy_gettext("User can update publish queue"),
        ),
        Privilege(
            name="subscribers",
            label=lazy_gettext("Subscribers"),
            description=lazy_gettext("User can manage subscribers"),
        ),
    ],
)

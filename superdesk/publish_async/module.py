import logging
from importlib import import_module

from quart_babel import lazy_gettext

from superdesk.core import get_config
from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.module import Module
from superdesk.core.privileges import Privilege

from .resources.module import (
    content_filters_resource_config,
    filter_conditions_resource_config,
    products_resource_config,
    publish_queue_resource_config,
    sequences_resource_config,
    subscribers_resource_config,
    subscriber_token_resource_config,
)

from .view import publish_endpoints
from .commands import *  # noqa
from . import get_exchange_factory


logger = logging.getLogger(__name__)


def init_publishing_module(app: SuperdeskAsyncApp):
    exchange_factory = get_exchange_factory()
    for module_path in get_config(list[str], "PUBLISH_MODULES"):
        imported_module = import_module(module_path)
        components = getattr(imported_module, "publish_components", None)
        if not components:
            logger.warning(f"Module {module_path} has no publish_components")
            continue

        for component in components:
            exchange_factory.register_component(component)

    app.on_app_shutdown.connect(exchange_factory.on_app_shutdown)


module = Module(
    name="superdesk.publish_async",
    init=init_publishing_module,
    endpoints=[publish_endpoints],
    resources=[
        content_filters_resource_config,
        filter_conditions_resource_config,
        products_resource_config,
        publish_queue_resource_config,
        sequences_resource_config,
        subscribers_resource_config,
        subscriber_token_resource_config,
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

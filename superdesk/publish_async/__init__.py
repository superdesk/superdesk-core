from quart_babel import lazy_gettext

import superdesk
from superdesk.core.utils import load_class_from_config
from superdesk.types import PublishExchangeFactory


__all__ = ["get_exchange_factory"]


def get_exchange_factory() -> PublishExchangeFactory:
    """
    Gets an instance of PublishExchangeFactory.

    This function retrieves a class implementation of PublishExchangeFactory from the
    configuration using the `load_class_from_config` function. It then initializes and
    returns an instance of the retrieved factory class.

    Example publishing an item::

        from superdesk.types import PublishRequest, PublishSenderType
        from superdesk.publish_async import get_exchange_factory

        async def publish_some_item(item: dict) -> bool:
            response = await get_exchange_factory().send(
                PublishRequest(
                    item=item,
                    item_id=item["_id"],
                    item_type=item["type"],
                    operation="publish",
                    published_state="published",
                    publish_to_content_api=True,
                    sender_type=PublishSenderType.INGEST_RULE
                )
            )
            return response.routed

    :return: An instance of PublishExchangeFactory, based on the ``PUBLISH_EXCHANGE_FACTORY`` config
    """

    factory_class = load_class_from_config(PublishExchangeFactory, "PUBLISH_EXCHANGE_FACTORY")
    return factory_class()


def init_app(app) -> None:
    superdesk.privilege(
        name="content_filters",
        label=lazy_gettext("Content Filters"),
        description=lazy_gettext("User can manage content filters"),
    )
    superdesk.privilege(
        name="products",
        label=lazy_gettext("Products Management"),
        description=lazy_gettext("User can manage product lists."),
    )

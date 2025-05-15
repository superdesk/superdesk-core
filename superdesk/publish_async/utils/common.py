import logging

from bson import ObjectId

from superdesk.core import get_config
from superdesk.types import (
    SubscriberDestination,
    SubscribersResource,
    SubscriberType,
    PublishRequest,
    ContentFiltersResource,
    FilterConditionsResource,
    ProductsResource,
    ProductItemTestResult,
)
from superdesk.default_settings import PublishChannelConfig, ExchangeConfig
from superdesk.resource_fields import (
    ID_FIELD,
    GUID_FIELD,
    ITEM_TYPE,
    ITEM_OPERATION,
    SCHEDULE_SETTINGS,
    QUEUE_STATE,
    PUBLISH_SCHEDULE,
)

from .items import is_doc_targeted

PUBLISHED = "published"
ITEM_PUBLISH = "publish"
ERROR_MESSAGE = "error_message"


logger = logging.getLogger(__name__)


def get_publish_request_from_item(item: dict, operation_override: str | None = None) -> PublishRequest:
    return PublishRequest(
        item=item,
        item_id=item.get("item_id") or item.get(GUID_FIELD) or item[ID_FIELD],
        item_type=item.get(ITEM_TYPE) or "text",
        operation=operation_override or item.get(ITEM_OPERATION, "publish"),
        published_state="published",
    )


def item_target_matches_product_target(item: dict, product: ProductsResource) -> bool:
    """Returns boolean if the supplied item matches the product region/target"""

    # TODO-ASYNC: Fix circular import
    from ..filters import BasePublishExchangeFilter

    return BasePublishExchangeFilter().product_target_matches_item_target(get_publish_request_from_item(item), product)


def item_target_matches_subscriber_target(item: dict, subscriber: SubscribersResource) -> bool:
    """Returns boolean if the supplied item matches the target subscriber"""

    # TODO-ASYNC: Fix circular import
    from ..filters import BasePublishExchangeFilter

    return BasePublishExchangeFilter().subscriber_target_matches_item_target(
        get_publish_request_from_item(item), subscriber
    )


def get_publish_channel_config(item: dict, item_type: str, operation: str, sender_type: str) -> ExchangeConfig:
    """
    Determines and retrieves the publish channel configuration based on the provided
    parameters. This function evaluates a list of configured publish channels, applies
    various filters, and selects an appropriate configuration for the given parameters.
    If no channel matches, a default configuration is utilized.

    :param item: The item data to be evaluated against the specified filters.
    :param item_type: The type of the item to be matched with channel configuration.
    :param operation: The operation type to filter the applicable channel configuration.
    :param sender_type: The type representing the sender to match the channel configuration.
    :return: The resulting exchange configuration based on the evaluated publish channel criteria and default fallback.
    """

    channels = get_config(list[PublishChannelConfig], "PUBLISH_CHANNELS")
    config: ExchangeConfig | None = None
    default_config = get_config(ExchangeConfig, "DEFAULT_PUBLISH_CHANNEL").copy()

    i = 0
    for channel in channels:
        i += 1
        try:
            if channel.get("item_types") and item_type not in channel["item_types"]:
                continue
            elif channel.get("operations") and operation not in channel["operations"]:
                continue
            elif channel.get("sender_types") and sender_type not in channel["sender_types"]:
                continue
            elif channel.get("filter") and not channel["filter"](item):
                continue
        except Exception:
            logger.exception("Failed to check publish channel config")
            continue

        config = channel["config"].copy()
        break

    if config is None:
        config = default_config
    else:
        config["exchange"] = config.get("exchange", default_config["exchange"])
        config["filter"] = config.get("filter", default_config["filter"])
        config["formatter"] = config.get("formatter", default_config["formatter"])
        config["router"] = config.get("router", default_config["router"])
        config["polling"] = config.get("polling", default_config["polling"])

    return config


def item_matches_product_filters(item: dict, product: ProductsResource) -> bool:
    """Returns boolean if the supplied item matches the product filters

    Note: Make sure to initialise the PublishCache before running this function
    """

    # TODO-ASYNC: Fix circular import
    from ..filters import BasePublishExchangeFilter

    return BasePublishExchangeFilter().product_filter_matches_item(get_publish_request_from_item(item), product)


def test_products_against_item(item: dict) -> list[ProductItemTestResult]:
    """Iterates over all products to tests them against the supplied item.

    Note: Make sure to initialise the PublishCache before running this function
    """

    # TODO-ASYNC: Fix circular import
    from ..publish_cache import PublishCache

    publish_cache = PublishCache.get()
    item_id: str | None = item.get("item_id") or item.get("_id") or item.get("guid")
    assert item_id is not None
    cache_id = PublishCache.generate_cache_id("article", "products", item_id)

    results: list[ProductItemTestResult] | None = publish_cache.cache.get(cache_id)

    if not results:
        results = []
        for product in publish_cache.products.values():
            result = ProductItemTestResult(
                product_id=product.id,
                matched=True,
                name=product.name or "",
                reason="",
            )
            reason = ""
            if not item_target_matches_product_target(item, product):
                # Here it fails to match due to geo restriction
                # story has target_region and product has geo restriction
                result["matched"] = False

                if is_doc_targeted(item, "target_regions"):
                    reason = "Story has target_region"

                if product.geo_restrictions:
                    reason = "{} {}".format(reason, "Product has target_region")

            if not item_matches_product_filters(item, product):
                # Here it fails to match due to content filter
                reason = "Story does not match the filter"
                if product.content_filter and product.content_filter.filter_id:
                    content_filter = publish_cache.content_filters.get(product.content_filter.filter_id)
                    if content_filter:
                        reason = f"Story does not match the filter: {content_filter.name}"
                result["matched"] = False

            result["reason"] = reason
            results.append(result)
        publish_cache.cache[cache_id] = results

    return results


async def content_filter_to_elastic_query(doc: ContentFiltersResource, matching: bool = True) -> dict:
    # TODO-ASYNC: Fix this circular import
    from apps.content_filters.filter_condition.filter_condition import FilterCondition

    content_filter_service = ContentFiltersResource.get_service()
    filter_condition_service = FilterConditionsResource.get_service()
    expressions_list: list[dict] = []
    if matching:
        expressions = {"should": expressions_list}
    else:
        expressions = {"must_not": expressions_list}

    for expression in doc.content_filter or []:
        filter_conditions = {"must": [], "must_not": [{"term": {"state": "spiked"}}]}
        for filter_id in expression.expression.fc or []:
            current_filter_item = await filter_condition_service.find_by_id(filter_id)
            if not current_filter_item:
                # Should not happen, as we have validation on the model to prevent this
                continue
            current_filter_condition = FilterCondition.parse(current_filter_item.to_dict())
            elastic_query = current_filter_condition.get_elastic_query()
            if current_filter_condition.contains_not():
                filter_conditions["must_not"].append(elastic_query)
            else:
                filter_conditions["must"].append(elastic_query)

        for filter_id in expression.expression.pf or []:
            current_content_filter = await content_filter_service.find_by_id(filter_id)
            if not current_content_filter:
                # Should not happen, as we have validation on the model to prevent this
                continue
            elastic_query = await content_filter_to_elastic_query(current_content_filter)
            filter_conditions["must"].append(elastic_query)

        expressions_list.append({"bool": filter_conditions})

    return {"bool": expressions}


ContentApiSubscriber = SubscribersResource(
    id=ObjectId("67be81e46f53273f423a2801"),  # Use our own ID here, so it can be used across processes, restarts etc
    name="_Content_API_",
    subscriber_type=SubscriberType.ALL,
    email="fake@email.com",
    destinations=[
        SubscriberDestination(name="content api", format="ninjs", delivery_type="content_api"),
    ],
)

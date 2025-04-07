from typing import Any
import logging

from bson import ObjectId

from superdesk.core import get_config
from superdesk.types import SubscriberDestination, SubscribersResource, SubscriberType
from superdesk.default_settings import PublishChannelConfig, ExchangeConfig


logger = logging.getLogger(__name__)


def get_publish_celery_queue(context: str | None = None) -> str:
    """
    Gets the Celery queue name for publishing tasks based on the provided context.

    This function retrieves the Celery queue name using the given context to format
    the associated configuration key. If no context is provided, it defaults to
    using the "DEFAULT" context. The queue name is fetched from the application's
    configuration.

    :param context: Optional argument specifying the context to determine the Celery queue name.
    :return: The name of the Celery queue used for publishing tasks.
    :raises KeyError: If the configuration key for the specified context is missing from the application configuration.
    """

    if context is None:
        context = "DEFAULT"

    return get_config(str, f"PUBLISH_{context.upper()}_CELERY_QUEUE", "PUBLISH_DEFAULT_CELERY_QUEUE")


def get_high_priority_celery_queue(priority: bool | None = None) -> str:
    """
    Determines the appropriate Celery queue based on priority and configuration.

    If a high priority queue is enabled in the configuration and the priority
    flag is set, the function retrieves the name of the high priority queue
    from the configuration. Otherwise, it falls back to the default Celery
    queue for publishing tasks.

    :param priority: Optional argument indicating whether a high priority queue should be used.
    :return: The name of the appropriate Celery queue.
    """

    return (
        get_config(str, "HIGH_PRIORITY_QUEUE")
        if priority and get_config(bool, "HIGH_PRIORITY_QUEUE_ENABLED")
        else get_publish_celery_queue()
    )


def is_doc_targeted(item: dict, target: str | None = None) -> bool:
    """
    Determine if a given item dictionary includes targeted information.

    This function evaluates whether a specified target is present in the item
    dictionary or if any generic target-related fields contain data. It accepts
    an optional field name (target) to check for existence of information in
    that specific field, otherwise it defaults to checking multiple predefined
    keys in the item dictionary for any relevant content.

    :param item: A dictionary containing target-related data.
    :param target: Optional argument specifying the field to check for targeted information.
    :return: ``True`` if the targeted information is present in the specified field or default fields; ``False`` otherwise.
    """

    if target:
        return len(item.get(target, [])) > 0
    else:
        return (
            len(item.get("target_regions", []) + item.get("target_types", []) + item.get("target_subscribers", [])) > 0
        )


def get_codes(item: Any) -> set[str]:
    """
    Retrieve codes from an object attribute.

    This function attempts to extract and parse a 'codes' attribute from
    the provided object. The 'codes' attribute is expected to be a
    comma-separated string. Each code is stripped of whitespace, and
    only non-empty codes are included in the resulting set. If the
    provided object does not have a 'codes' attribute, the function
    returns an empty set.

    :param item: The object from which the 'codes' attribute is to be retrieved and parsed.
    :return: A set of unique, stripped codes. Returns an empty set if the 'codes' attribute is missing or empty.
    """

    try:
        codes: str = getattr(item, "codes", "") or ""
        return set([code.strip() for code in codes.split(",") if code.strip()])
    except AttributeError:
        return set()


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

    for channel in channels:
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
        config["exchange"] = config.get("exchange") or default_config["exchange"]
        config["filter"] = config.get("filter") or default_config["filter"]
        config["formatter"] = config.get("formatter") or default_config["formatter"]
        config["router"] = config.get("router") or default_config["router"]
        config["polling"] = config.get("polling") or default_config["polling"]

    return config


ContentApiSubscriber = SubscribersResource(
    id=ObjectId("67be81e46f53273f423a2801"),  # Use our own ID here, so it can be used across processes, restarts etc
    name="_Content_API_",
    subscriber_type=SubscriberType.ALL,
    email="fake@email.com",
    destinations=[
        SubscriberDestination(name="content api", format="ninjs", delivery_type="content_api"),
    ],
)

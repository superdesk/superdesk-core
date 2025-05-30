from typing import cast
from bson import ObjectId

from superdesk.core import get_config
from superdesk.core.resources import ResourceCursorAsync
from superdesk.types import PublishQueueState, PublishQueueResource, PublishRequestResponse, SubscribersResource
from superdesk.utc import utcnow


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


def _get_queue_lookup(retries: bool = False, priority: bool | None = None) -> dict:
    priority_lookup = {"priority": priority if priority else {"$ne": True}}
    if retries:
        return {
            "$and": [
                {"state": PublishQueueState.RETRYING},
                {"next_retry_attempt_at": {"$lte": utcnow()}},
                priority_lookup,
            ]
        }
    return {
        "$and": [
            {"state": PublishQueueState.PENDING},
            priority_lookup,
        ]
    }


async def get_queue_items(
    retries: bool = False, subscriber_id: ObjectId | None = None, priority: bool | None = None
) -> ResourceCursorAsync[PublishQueueResource]:
    lookup = _get_queue_lookup(retries, priority)
    if subscriber_id:
        lookup["$and"].append({"subscriber_id": subscriber_id})

    return await PublishQueueResource.get_service().find(
        lookup,
        max_results=cast(int, get_config(int, "MAX_TRANSMIT_QUERY_LIMIT")),  # limit per subscriber now
        sort=[("_created", 1), ("published_seq_num", 1)],
    )


async def get_subscribers_for_previously_sent_items(
    response: PublishRequestResponse, lookup: dict
) -> tuple[list[SubscribersResource], dict[ObjectId, set[str]], dict[ObjectId | str, list[str]]]:
    """
    Retrieves subscribers and related information for items that were previously sent.

    This asynchronous function fetches active subscribers and associates them with
    previously sent items. It processes the provided response and performs a lookup
    based on the given criteria. The function manages subscriber codes and associated
    items while identifying subscribers with content API delivery type.

    :param response: The current publish request response object which will be
        updated to include content API subscribers.
    :param lookup: A dictionary containing lookup/filter criteria to search queued items.
    :return: A tuple containing the following:
        - ``list[SubscribersResource]``: List of active subscribers matching the criteria.
        - ``dict[ObjectId, set[str]]``: Mapping of subscriber IDs to their unique codes.
        - ``dict[ObjectId | str, list[str]]``: Mapping of subscriber IDs to associated items.
    """

    # TODO-ASYNC: Fix circular import
    from ..publish_cache import PublishCache

    cache = PublishCache.get()
    subscriber_codes: dict[ObjectId, set[str]] = {}
    associations: dict[ObjectId | str, list[str]] = {}
    active_subscribers = cache.subscribers.values()
    queued_items = await PublishQueueResource.get_service().search(lookup)

    subscriber_ids: dict[ObjectId, bool] = {}
    async for queue_item in queued_items:
        subscriber_id = queue_item.subscriber_id
        if not subscriber_ids.get(subscriber_id):
            subscriber_ids[subscriber_id] = False
            if queue_item.destination and queue_item.destination.delivery_type == "content_api":
                subscriber_ids[subscriber_id] = True

        subscriber_codes[subscriber_id] = set(queue_item.codes or [])
        if queue_item.associated_items:
            associations[subscriber_id] = list(
                set(associations.get(subscriber_id, [])) | set(queue_item.associated_items)
            )

    subscribers: list[SubscribersResource] = [
        subscriber for subscriber in active_subscribers if subscriber.id in subscriber_ids
    ]

    for subscriber in subscribers:
        if subscriber_ids.get(subscriber.id):
            response.content_api_subscribers.add(subscriber.id)

    return subscribers, subscriber_codes, associations

from typing import TypedDict
import logging
import traceback

from superdesk.types import (
    SubscribersResource,
    SequencesResource,
    SubscriberDestination,
    ProductsResource,
)
from superdesk.core import get_app_config
from superdesk.resource import build_custom_hateoas
from superdesk.utils import get_dict_hash

from superdesk.publish_async.filter_conditions.utils import check_similar_filter_conditions
from superdesk.publish_async.content_filters.utils import get_content_filters_by_filter_condition


logger = logging.getLogger(__name__)


class GetFilterConditionResponse(TypedDict):
    filter_conditions: list[dict]
    content_filters: list[dict]
    products: list[dict]
    selected_subscribers: list[dict]


async def generate_sequence_number(subscriber: SubscribersResource) -> int:
    """
    Generates Published Sequence Number for the passed subscriber
    """

    assert subscriber is not None, "Subscriber can't be null"
    min_seq_number = 1
    max_seq_number = get_app_config("MAX_VALUE_OF_PUBLISH_SEQUENCE")
    if subscriber.sequence_num_settings:
        min_seq_number = subscriber.sequence_num_settings.min
        max_seq_number = subscriber.sequence_num_settings.max

    return await get_next_sequence_number(
        key_name="subscribers_{_id})".format(_id=subscriber.id),
        max_seq_number=max_seq_number,
        min_seq_number=min_seq_number,
    )


async def get_next_sequence_number(
    key_name: str | None, max_seq_number: int | None = None, min_seq_number: int = 1
) -> int:
    """
    Generates Sequence Number

    :param key_name: key to identify the sequence
    :param max_seq_number: default None, maximal possible value, None means no upper limit
    :param min_seq_number: default 1, init value, sequence will start from the NEXT one
    :returns: sequence number
    """
    if not key_name:
        logger.error("Empty sequence key is used: {}".format("\n".join(traceback.format_stack())))
        raise KeyError("Sequence key cannot be empty")

    target_resource = SequencesResource.get_service()
    # target_resource.mongo.find_one_and_update()
    sequence_number = (
        await target_resource.mongo_async.find_one_and_update(
            {"key": key_name}, update={"$inc": {"sequence_number": 1}}, upsert=True, new=True
        )
    ).get("sequence_number")

    if max_seq_number:
        if sequence_number > max_seq_number:
            await target_resource.mongo_async.find_one_and_update(
                {"key": key_name}, update={"$set": {"sequence_number": min_seq_number}}
            )

            sequence_number = min_seq_number

    return sequence_number


def get_subscriber_destination_id(subscriber_destination: SubscriberDestination | dict) -> str:
    destination_dict = (
        subscriber_destination.to_dict()
        if isinstance(subscriber_destination, SubscriberDestination)
        else subscriber_destination
    )
    if destination_dict.get("_id"):
        return destination_dict["_id"]
    return get_dict_hash(destination_dict)


async def _get_subscribers_by_filter_condition(filter_condition: dict) -> GetFilterConditionResponse:
    """
    Searches all subscribers that has a content filter with the given filter condition

    If filter condition is used in a global filter then it returns all
    subscribers that not disabled the global filter.
    :param filter_condition: Filter condition to test
    :return: List of subscribers
    """
    all_subscribers: list[SubscribersResource] = await SubscribersResource.get_service().get_all_list()
    selected_products: dict[str, dict] = {}
    selected_subscribers: dict[str, dict] = {}
    selected_content_filters: dict[str, dict] = {}
    existing_products: list[ProductsResource] = await ProductsResource.get_service().get_all_list()

    existing_filter_conditions = await check_similar_filter_conditions(filter_condition)
    for similar_filter_condition in existing_filter_conditions:
        existing_content_filters = await get_content_filters_by_filter_condition(similar_filter_condition.id)
        for pf in existing_content_filters:
            selected_content_filters[str(pf.id)] = pf.to_dict()

            if pf.is_global:
                for subscriber in all_subscribers:
                    gfs = subscriber.global_filters or {}
                    if gfs.get(str(pf.id), True):
                        subscriber_dict = subscriber.to_dict()
                        build_custom_hateoas(
                            {"self": {"title": "subscribers", "href": "/subscribers/{_id}"}}, subscriber_dict
                        )
                        selected_subscribers[str(subscriber.id)] = subscriber_dict

            for product in existing_products:
                if (
                    product.content_filter
                    and product.content_filter.filter_id
                    and product.content_filter.filter_id == pf.id
                ):
                    selected_products[str(product.id)] = product.to_dict()

            for subscriber in all_subscribers:
                all_subscriber_products = list(set(subscriber.products or []) | set(subscriber.api_products or []))
                for p in all_subscriber_products:
                    if str(p) in selected_products:
                        subscriber_dict = subscriber.to_dict()
                        build_custom_hateoas(
                            {"self": {"title": "subscribers", "href": "/subscribers/{_id}"}}, subscriber_dict
                        )
                        selected_subscribers[str(subscriber.id)] = subscriber_dict

    return {
        "filter_conditions": [item.to_dict() for item in existing_filter_conditions],
        "content_filters": list(selected_content_filters.values()),
        "products": list(selected_products.values()),
        "selected_subscribers": list(selected_subscribers.values()),
    }

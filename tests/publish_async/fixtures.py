from bson import ObjectId
from superdesk.types import (
    SubscriberType,
    FilterConditionsResource,
    FilterConditionOperator,
    ContentFiltersResource,
    ContentFilter,
    ContentFilterExpression,
    ProductsResource,
    ProductContentFilter,
    ProductFilterType,
    SubscribersResource,
    SubscriberDestination,
)

FILTER_CONDITION_IDS = [ObjectId(), ObjectId()]
CONTENT_FILTER_IDS = [ObjectId(), ObjectId()]
PRODUCT_IDS = [ObjectId(), ObjectId()]
SUBSCRIBER_IDS = [ObjectId(), ObjectId(), ObjectId()]

FILTER_CONDITIONS = [
    FilterConditionsResource(
        id=FILTER_CONDITION_IDS[0],
        field="headline",
        operator=FilterConditionOperator.LIKE,
        value="weather",
        name="filter-weather",
    ),
    FilterConditionsResource(
        id=FILTER_CONDITION_IDS[1],
        field="anpa_category",
        operator=FilterConditionOperator.IN,
        value="sports",
        name="filter-sports",
    ),
]

CONTENT_FILTERS = [
    ContentFiltersResource(
        id=CONTENT_FILTER_IDS[0],
        content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0]]))],
        name="content-filter-weather",
    ),
    ContentFiltersResource(
        id=CONTENT_FILTER_IDS[1],
        content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[1]]))],
        name="content-filter-sports",
    ),
]

PRODUCTS = [
    ProductsResource(
        id=PRODUCT_IDS[0],
        content_filter=ProductContentFilter(filter_id=CONTENT_FILTER_IDS[0], filter_type=ProductFilterType.PERMITTING),
        name="product-weather",
        codes="prod-weather1,prod-weather2",
    ),
    ProductsResource(
        id=PRODUCT_IDS[1],
        content_filter=ProductContentFilter(filter_id=CONTENT_FILTER_IDS[1], filter_type=ProductFilterType.PERMITTING),
        name="product-sports",
        codes="prod-sports1,prod-sports2",
    ),
]

SUBSCRIBERS = [
    SubscribersResource(
        id=SUBSCRIBER_IDS[0],
        products=[PRODUCT_IDS[0]],
        name="subscriber-weather",
        subscriber_type=SubscriberType.WIRE,
        email="sub1@subscribers.org",
        is_active=True,
        destinations=[
            SubscriberDestination(
                name="weather-destination",
                format="text",
                delivery_type="file",
            ),
        ],
        codes="sub-weather1,sub-weather2",
    ),
    SubscribersResource(
        id=SUBSCRIBER_IDS[1],
        products=[PRODUCT_IDS[1]],
        name="subscriber-sports",
        subscriber_type=SubscriberType.DIGITAL,
        email="sub2@subscribers.org",
        is_active=True,
        destinations=[
            SubscriberDestination(
                name="sports-destination",
                format="text",
                delivery_type="file",
            ),
        ],
        codes="sub-sports1,sub-sports2",
    ),
    SubscribersResource(
        id=SUBSCRIBER_IDS[2],
        products=[PRODUCT_IDS[0], PRODUCT_IDS[1]],
        name="subscriber-all",
        subscriber_type=SubscriberType.ALL,
        email="all@subscribers.org",
        is_active=True,
        destinations=[
            SubscriberDestination(
                name="all-destination",
                format="text",
                delivery_type="file",
            ),
        ],
        codes="sub-all1,sub-all2",
    ),
]

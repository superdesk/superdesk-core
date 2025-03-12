from bson import ObjectId

from superdesk.types import (
    PublishRequest,
    PublishRequestResponse,
    FilterConditionsResource,
    ContentFiltersResource,
    ProductsResource,
    SubscribersResource,
    SubscriberType,
    ContentType,
)
from superdesk.core.utils import generate_guid, GUID_NEWSML
from superdesk.publish_async.publish_cache import PublishCache
from superdesk.publish_async.filters import BasePublishExchangeFilter

from superdesk.tests import TestCase

from ..fixtures import (
    FILTER_CONDITIONS,
    CONTENT_FILTERS,
    PRODUCTS,
    PRODUCT_IDS,
    SUBSCRIBERS,
    SUBSCRIBER_IDS,
)


class BasePublishFilterTestCase(TestCase):
    filter: BasePublishExchangeFilter

    async def asyncSetUp(self):
        await super().asyncSetUp()

        await FilterConditionsResource.get_service().create(FILTER_CONDITIONS)
        await ContentFiltersResource.get_service().create(CONTENT_FILTERS)
        await ProductsResource.get_service().create(PRODUCTS)
        await SubscribersResource.get_service().create(SUBSCRIBERS)
        await PublishCache().init(force=True)
        self.filter = BasePublishExchangeFilter()

    async def run_test_filter(self, item: dict) -> PublishRequestResponse:
        request = PublishRequest(
            item=item,
            item_id=generate_guid(type=GUID_NEWSML),
            operation="publish",
            published_state="published",
            item_type=ContentType.TEXT,
        )
        response = PublishRequestResponse()
        await self.filter.filter_subscribers(request, response)
        return response

    async def test_filter_no_matches(self):
        # Try with finance item (no subscribers)
        response = await self.run_test_filter(
            {"headline": "finance stuff", "anpa_category": [{"qcode": "finance", "name": "Finance"}]}
        )

        # Make sure none of the response details contain any matches (products, subscribers, codes)
        self.assertEqual(response.subscribers, [])
        self.assertSetEqual(response.content_api_subscribers, set())
        self.assertDictEqual(response.product_codes, {})
        self.assertDictEqual(response.subscriber_codes, {})
        self.assertListEqual(response.matched_products, [])
        self.assertListEqual(response.matched_api_products, [])

    async def test_filter_weather_matches(self):
        # Try with weather item
        response = await self.run_test_filter(
            {"headline": "Sydney weather", "anpa_category": [{"qcode": "weather", "name": "Weather"}]}
        )

        # Make sure the response details contain correct matches (products, subscribers, codes)
        self.assertListEqual(
            sorted([subscriber.id for subscriber in response.subscribers]), [SUBSCRIBER_IDS[0], SUBSCRIBER_IDS[2]]
        )
        self.assertSetEqual(response.content_api_subscribers, set())
        self.assertDictEqual(response.product_codes, {PRODUCT_IDS[0]: {"prod-weather1", "prod-weather2"}})
        self.assertDictEqual(
            response.subscriber_codes,
            {
                SUBSCRIBER_IDS[0]: {"prod-weather1", "prod-weather2", "sub-weather1", "sub-weather2"},
                SUBSCRIBER_IDS[2]: {"prod-weather1", "prod-weather2", "sub-all1", "sub-all2"},
            },
        )
        self.assertListEqual(sorted([product.id for product in response.matched_products]), [PRODUCT_IDS[0]])
        self.assertListEqual(response.matched_api_products, [])

    async def test_filter_sports_matches(self):
        # Try with sports item
        response = await self.run_test_filter(
            {"headline": "Sydney sports", "anpa_category": [{"qcode": "sports", "name": "Sports"}]}
        )

        # Make sure the response details contain correct matches (products, subscribers, codes)
        self.assertListEqual(
            sorted([subscriber.id for subscriber in response.subscribers]), [SUBSCRIBER_IDS[1], SUBSCRIBER_IDS[2]]
        )
        self.assertSetEqual(response.content_api_subscribers, set())
        self.assertDictEqual(response.product_codes, {PRODUCT_IDS[1]: {"prod-sports1", "prod-sports2"}})
        self.assertDictEqual(
            response.subscriber_codes,
            {
                SUBSCRIBER_IDS[1]: {"prod-sports1", "prod-sports2", "sub-sports1", "sub-sports2"},
                SUBSCRIBER_IDS[2]: {"prod-sports1", "prod-sports2", "sub-all1", "sub-all2"},
            },
        )
        self.assertListEqual(sorted([product.id for product in response.matched_products]), [PRODUCT_IDS[1]])
        self.assertListEqual(response.matched_api_products, [])

    async def test_multiple_matches(self):
        # Try with weather item
        response = await self.run_test_filter(
            {
                "headline": "Sport weather update",
                "anpa_category": [
                    {"qcode": "weather", "name": "Weather"},
                    {"qcode": "sports", "name": "Sports"},
                ],
            }
        )

        # Make sure the response details contain correct matches (products, subscribers, codes)
        self.assertListEqual(
            sorted([subscriber.id for subscriber in response.subscribers]),
            [SUBSCRIBER_IDS[0], SUBSCRIBER_IDS[1], SUBSCRIBER_IDS[2]],
        )
        self.assertSetEqual(response.content_api_subscribers, set())
        self.assertDictEqual(
            response.product_codes,
            {
                PRODUCT_IDS[0]: {"prod-weather1", "prod-weather2"},
                PRODUCT_IDS[1]: {"prod-sports1", "prod-sports2"},
            },
        )
        self.assertDictEqual(
            response.subscriber_codes,
            {
                SUBSCRIBER_IDS[0]: {"prod-weather1", "prod-weather2", "sub-weather1", "sub-weather2"},
                SUBSCRIBER_IDS[1]: {"prod-sports1", "prod-sports2", "sub-sports1", "sub-sports2"},
                SUBSCRIBER_IDS[2]: {
                    "prod-weather1",
                    "prod-weather2",
                    "prod-sports1",
                    "prod-sports2",
                    "sub-all1",
                    "sub-all2",
                },
            },
        )
        self.assertListEqual(
            sorted([product.id for product in response.matched_products]), [PRODUCT_IDS[0], PRODUCT_IDS[1]]
        )
        self.assertListEqual(response.matched_api_products, [])

    async def test_content_api_matches(self):
        # Update Subscribers to add Content API products, and reset the cache
        subscriber_service = SubscribersResource.get_service()
        await subscriber_service.update(SUBSCRIBER_IDS[0], {"products": [], "api_products": [PRODUCT_IDS[0]]})
        await subscriber_service.update(SUBSCRIBER_IDS[1], {"api_products": [PRODUCT_IDS[1]]})
        await PublishCache.init(force=True)

        response = await self.run_test_filter(
            {
                "headline": "Sport weather update",
                "anpa_category": [
                    {"qcode": "weather", "name": "Weather"},
                    {"qcode": "sports", "name": "Sports"},
                ],
            }
        )
        # Make sure the response details contain correct matches (products, subscribers, codes)
        self.assertListEqual(
            [subscriber.id for subscriber in response.subscribers],
            [SUBSCRIBER_IDS[0], SUBSCRIBER_IDS[1], SUBSCRIBER_IDS[2]],
        )
        self.assertListEqual(sorted(response.content_api_subscribers), [SUBSCRIBER_IDS[0], SUBSCRIBER_IDS[1]])
        self.assertDictEqual(
            response.product_codes,
            {
                PRODUCT_IDS[0]: {"prod-weather1", "prod-weather2"},
                PRODUCT_IDS[1]: {"prod-sports1", "prod-sports2"},
            },
        )
        self.assertDictEqual(
            response.subscriber_codes,
            {
                SUBSCRIBER_IDS[0]: {"prod-weather1", "prod-weather2", "sub-weather1", "sub-weather2"},
                SUBSCRIBER_IDS[1]: {"prod-sports1", "prod-sports2", "sub-sports1", "sub-sports2"},
                SUBSCRIBER_IDS[2]: {
                    "prod-weather1",
                    "prod-weather2",
                    "prod-sports1",
                    "prod-sports2",
                    "sub-all1",
                    "sub-all2",
                },
            },
        )
        self.assertListEqual(
            sorted([product.id for product in response.matched_products]), [PRODUCT_IDS[0], PRODUCT_IDS[1]]
        )
        self.assertListEqual(
            sorted(product.id for product in response.matched_api_products), [PRODUCT_IDS[0], PRODUCT_IDS[1]]
        )

    def test_subscriber_type_matches_request_type(self):
        # Map of Subscriber.id to (PublishRequest.item_type, PublishRequest.target_media_type)
        # These are the PublishRequest conditions the respective Subscriber **WILL NOT** receive
        excluded_subscribers: dict[ObjectId, list[tuple[ContentType, SubscriberType | None]]] = {
            # Test subscriber_type == SubscriberType.WIRE
            SUBSCRIBER_IDS[0]: [
                (ContentType.TEXT, SubscriberType.DIGITAL),
                (ContentType.PREFORMATTED, SubscriberType.DIGITAL),
                (ContentType.AUDIO, None),
                (ContentType.AUDIO, SubscriberType.DIGITAL),
                (ContentType.VIDEO, None),
                (ContentType.VIDEO, SubscriberType.DIGITAL),
                (ContentType.PICTURE, None),
                (ContentType.PICTURE, SubscriberType.DIGITAL),
                (ContentType.GRAPHIC, None),
                (ContentType.GRAPHIC, SubscriberType.DIGITAL),
                (ContentType.COMPOSITE, None),
                (ContentType.COMPOSITE, SubscriberType.DIGITAL),
                (ContentType.EVENT, None),
                (ContentType.EVENT, SubscriberType.DIGITAL),
                (ContentType.PLANNING, None),
                (ContentType.PLANNING, SubscriberType.DIGITAL),
                (ContentType.FEATURED_PLANNING, None),
                (ContentType.FEATURED_PLANNING, SubscriberType.DIGITAL),
            ],
            # Test subscriber_type == SubscriberType.DIGITAL
            SUBSCRIBER_IDS[1]: [
                (ContentType.TEXT, SubscriberType.WIRE),
                (ContentType.PREFORMATTED, SubscriberType.WIRE),
                (ContentType.AUDIO, SubscriberType.WIRE),
                (ContentType.VIDEO, SubscriberType.WIRE),
                (ContentType.PICTURE, SubscriberType.WIRE),
                (ContentType.GRAPHIC, SubscriberType.WIRE),
                (ContentType.COMPOSITE, SubscriberType.WIRE),
                (ContentType.EVENT, SubscriberType.WIRE),
                (ContentType.PLANNING, SubscriberType.WIRE),
                (ContentType.FEATURED_PLANNING, SubscriberType.WIRE),
            ],
            # Test subscriber_type == SubscriberType.ALL - receives all items
            SUBSCRIBER_IDS[2]: [],
        }

        for item_type in ContentType:
            for subscriber_type in list(SubscriberType) + [None]:
                for subscriber in SUBSCRIBERS:
                    request = PublishRequest(
                        item={},
                        item_id=generate_guid(type=GUID_NEWSML),
                        operation="publish",
                        published_state="published",
                        item_type=item_type,
                        target_media_type=subscriber_type,
                    )
                    actual_result = self.filter.subscriber_type_matches_request_type(request, subscriber)
                    expected_result = (item_type, subscriber_type) not in excluded_subscribers.get(subscriber.id, [])

                    self.assertEqual(
                        actual_result,
                        expected_result,
                        f"Failed for "
                        f"subscriber={subscriber.name} "
                        f"content_type={item_type}, "
                        f"subscriber_type={subscriber_type}",
                    )

    def test_subscriber_target_matches_item_target(self):
        pass

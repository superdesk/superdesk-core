from superdesk.types import PublishExchangeFactory, ContentType, PublishRequest
from superdesk.default_settings import ExchangeConfig
from superdesk.publish_async import get_exchange_factory
from superdesk.publish_async.utils import get_publish_channel_config
from superdesk.publish_async.exchanges import BasicPublishExchange
from superdesk.publish_async.filters import BasePublishExchangeFilter
from superdesk.publish_async.formatters import BasePublishExchangeFormatter
from superdesk.publish_async.routers import CeleryPublishRouter

from superdesk.tests import TestCase


class PublishChannelConfigTestCase(TestCase):
    factory: PublishExchangeFactory

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.factory = get_exchange_factory()

    async def test_default_components(self):
        exchange = self.factory.get_exchange(
            PublishRequest(
                item={},
                item_id="abcd123",
                operation="publish",
                published_state="published",
                item_type="event",
            )
        )
        self.assertIsInstance(exchange, BasicPublishExchange)
        self.assertIsInstance(exchange._filter, BasePublishExchangeFilter)
        self.assertIsInstance(exchange._formatter, BasePublishExchangeFormatter)
        self.assertIsInstance(exchange._router, CeleryPublishRouter)

    async def test_get_publish_channel_config(self):
        item_types = [
            ContentType.TEXT,
            ContentType.PREFORMATTED,
            ContentType.AUDIO,
            ContentType.VIDEO,
            ContentType.PICTURE,
            ContentType.GRAPHIC,
            ContentType.COMPOSITE,
            ContentType.EVENT,
            ContentType.PLANNING,
            ContentType.FEATURED_PLANNING,
        ]
        operations = [
            "publish",
            "correct",
            "kill",
            "takedown",
            "unpublish",
            "being_corrected",
            "resend",
        ]

        self.assertEqual(
            get_publish_channel_config({}, ContentType.TEXT, "publish", "api"),
            ExchangeConfig(
                exchange="content",
                filter="content",
                formatter="default",
                router="asyncio",
                polling=True,
            ),
        )

        # self.assertEqual(
        #     get_publish_channel_config({}, ContentType.TEXT, "resend", "api"),
        #     ExchangeConfig(
        #         exchange="content",
        #         filter="resend",
        #         formatter="default",
        #         router="asyncio",
        #         polling=True,
        #     )
        # )

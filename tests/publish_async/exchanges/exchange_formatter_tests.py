from bson import ObjectId

from superdesk.tests import TestCase
from superdesk.types import (
    SubscribersResource,
    SubscriberType,
    SubscriberDestination,
    PublishRequest,
    PublishRequestResponse,
    PublishQueueResource,
    PublishQueueState,
)
from superdesk.publish_async.formatters import BasePublishExchangeFormatter
from superdesk.publish.formatters import Formatter, NINJS2Formatter, FormatReturnType


class MockFormatter(Formatter):
    type = "mock"
    name = "Mock"
    use_cache = True

    async def format(self, article: dict, subscriber: dict | None, codes: list | None = None) -> FormatReturnType:
        raise Exception("Mock formatter failed")


class BaseExchangeFormatterTestCase(TestCase):
    formatter: BasePublishExchangeFormatter
    subscriber: SubscribersResource

    async def asyncSetUp(self):
        await super().asyncSetUp()

        self.subscriber = SubscribersResource(
            id=ObjectId(),
            name="Mock Subscriber",
            products=[],
            subscriber_type=SubscriberType.WIRE,
            email="mock@subscribers.test",
            is_active=True,
            destinations=[
                SubscriberDestination(
                    _id="dest_1",
                    name="Mock 1 Destination",
                    format=MockFormatter.type,
                    delivery_type="file",
                ),
                SubscriberDestination(
                    _id="dest_2",
                    name="NINJS Destination",
                    format=NINJS2Formatter.type,
                    delivery_type="file",
                ),
                SubscriberDestination(
                    _id="dest_3",
                    name="Mock 3 Destination",
                    format=MockFormatter.type,
                    delivery_type="file",
                ),
            ],
        )

        await SubscribersResource.get_service().create([self.subscriber])

        self.formatter = BasePublishExchangeFormatter()

    async def test_stores_formatter_errors_in_publish_queue_entry(self):
        item = dict(_id="abcd123", guid="abcd123", type="text", _current_version=1)
        request = PublishRequest(
            item=item,
            item_id=item["_id"],
            operation="publish",
            published_state="published",
            item_type=item["type"],
        )

        await self.formatter.get_tasks_for_subscriber(request, item, self.subscriber, PublishRequestResponse(), {})

        publish_queue = {queue.destination._id: queue async for queue in PublishQueueResource.get_service().get_all()}
        self.assertEqual(len(publish_queue), 3)

        self.assertEqual(publish_queue["dest_1"].state, PublishQueueState.ERROR)
        self.assertEqual(publish_queue["dest_1"].error_message, "Mock formatter failed")

        self.assertEqual(publish_queue["dest_2"].state, PublishQueueState.ROUTING)

        self.assertEqual(publish_queue["dest_3"].state, PublishQueueState.ERROR)
        self.assertEqual(publish_queue["dest_3"].error_message, "Mock formatter failed")

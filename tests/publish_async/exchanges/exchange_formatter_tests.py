from bson import ObjectId
from datetime import timedelta
from unittest import mock

from superdesk.tests import TestCase
from superdesk.utc import utcnow
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
from superdesk.metadata.item import INGEST_ID
from superdesk import get_resource_service
from superdesk.lifecycle_timing import to_epoch_ms


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
            item_id="abcd123",
            operation="publish",
            published_state="published",
            item_type="text",
        )

        await self.formatter.get_tasks_for_subscriber(request, item, self.subscriber, PublishRequestResponse(), {})

        publish_queue = {
            queue.destination._id: queue
            async for queue in PublishQueueResource.get_service().get_all()
            if queue.destination
        }
        self.assertEqual(len(publish_queue), 3)

        self.assertEqual(publish_queue["dest_1"].state, PublishQueueState.ERROR)
        self.assertEqual(publish_queue["dest_1"].error_message, "Mock formatter failed")

        self.assertEqual(publish_queue["dest_2"].state, PublishQueueState.ROUTING)

        self.assertEqual(publish_queue["dest_3"].state, PublishQueueState.ERROR)
        self.assertEqual(publish_queue["dest_3"].error_message, "Mock formatter failed")

    async def test_sets_queue_lifecycle_start_from_lifecycle_started_at(self):
        lifecycle_started_at = utcnow() - timedelta(minutes=10)
        item = {
            "_id": "lifecycle-ingest",
            "guid": "lifecycle-ingest",
            "type": "text",
            "_current_version": 1,
            "lifecycle_timing": {"lifecycle_started_at": lifecycle_started_at},
        }
        request = PublishRequest(
            item=item,
            item_id=item["_id"],
            operation="publish",
            published_state="published",
            item_type=item["type"],
        )

        await self.formatter.get_tasks_for_subscriber(request, item, self.subscriber, PublishRequestResponse(), {})
        publish_queue = {
            queue.destination._id: queue
            async for queue in PublishQueueResource.get_service().get_all()
            if queue.destination
        }

        self.assertEqual(lifecycle_started_at, publish_queue["dest_2"].lifecycle_started_at)

    async def test_sets_queue_lifecycle_start_from_request_when_filtered_item_drops_timing(self):
        lifecycle_started_at = utcnow() - timedelta(minutes=7)
        source_item = {
            "_id": "lifecycle-filtered",
            "guid": "lifecycle-filtered",
            "type": "text",
            "_current_version": 1,
            "lifecycle_timing": {"lifecycle_started_at": lifecycle_started_at},
        }
        request = PublishRequest(
            item=source_item,
            item_id=source_item["_id"],
            operation="publish",
            published_state="published",
            item_type=source_item["type"],
        )

        filtered_item = {
            "_id": source_item["_id"],
            "guid": source_item["guid"],
            "type": source_item["type"],
            "_current_version": source_item["_current_version"],
        }

        with mock.patch.object(self.formatter, "filter_item_fields", return_value=filtered_item):
            await self.formatter.get_request_tasks(request, PublishRequestResponse(subscribers=[self.subscriber]))

        publish_queue = {
            queue.destination._id: queue
            async for queue in PublishQueueResource.get_service().get_all()
            if queue.destination
        }

        self.assertEqual(lifecycle_started_at, publish_queue["dest_2"].lifecycle_started_at)

    async def test_fallbacks_to_ingest_doc_lifecycle_start_when_missing_on_item(self):
        lifecycle_started_at = utcnow() - timedelta(minutes=9)
        ingest_id = "ingest-source-1"

        item = {
            "_id": "lifecycle-fallback",
            "guid": "lifecycle-fallback",
            "type": "text",
            "_current_version": 1,
            "ingest_provider": "5ffeb066bc16d5875dc53081",
            INGEST_ID: ingest_id,
            "lifecycle_timing": {},
        }
        request = PublishRequest(
            item=item,
            item_id=item["_id"],
            operation="publish",
            published_state="published",
            item_type=item["type"],
        )

        ingest_service = get_resource_service("ingest")
        with mock.patch.object(
            ingest_service,
            "find_one_async",
            return_value={"lifecycle_timing": {"lifecycle_started_at": lifecycle_started_at}},
        ):
            await self.formatter.get_tasks_for_subscriber(request, item, self.subscriber, PublishRequestResponse(), {})

        publish_queue = {
            queue.destination._id: queue
            async for queue in PublishQueueResource.get_service().get_all()
            if queue.destination
        }

        self.assertEqual(lifecycle_started_at, publish_queue["dest_2"].lifecycle_started_at)

    async def test_sets_lifecycle_to_transmit_for_content_api_on_create(self):
        lifecycle_started_at = utcnow() - timedelta(seconds=8)
        completed_at = utcnow()
        subscriber = SubscribersResource(
            id=ObjectId(),
            name="Content API Subscriber",
            products=[],
            subscriber_type=SubscriberType.WIRE,
            email="content-api@subscribers.test",
            is_active=True,
            destinations=[
                SubscriberDestination(
                    _id="dest_content_api",
                    name="Content API",
                    format=NINJS2Formatter.type,
                    delivery_type="content_api",
                )
            ],
        )
        await SubscribersResource.get_service().create([subscriber])

        item = {
            "_id": "content-api-item",
            "guid": "content-api-item",
            "type": "text",
            "_current_version": 1,
            "lifecycle_timing": {"lifecycle_started_at": lifecycle_started_at},
        }
        request = PublishRequest(
            item=item,
            item_id=item["_id"],
            operation="publish",
            published_state="published",
            item_type=item["type"],
        )

        with mock.patch("superdesk.publish_async.formatters.base_exchange_formatter.utcnow", return_value=completed_at):
            await self.formatter.get_tasks_for_subscriber(request, item, subscriber, PublishRequestResponse(), {})

        publish_queue = {
            queue.destination._id: queue
            async for queue in PublishQueueResource.get_service().get_all()
            if queue.destination
        }

        queue_item = publish_queue["dest_content_api"]
        self.assertEqual(PublishQueueState.SUCCESS, queue_item.state)
        self.assertEqual(completed_at, queue_item.completed_at)
        self.assertEqual(to_epoch_ms(lifecycle_started_at), queue_item.lifecycle_started_ms)
        self.assertEqual(to_epoch_ms(completed_at), queue_item.completed_ms)
        self.assertEqual(8000, queue_item.lifecycle_to_transmit_ms)

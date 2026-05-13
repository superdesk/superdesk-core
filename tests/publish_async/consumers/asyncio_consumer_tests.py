from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

from bson import ObjectId

from superdesk.tests import TestCase
from superdesk.utc import utcnow
from superdesk.types import PublishQueueResource, PublishQueueState, SubscriberDestination
from superdesk.publish_async.consumers.asyncio_consumer import AsyncioPublishConsumer
from superdesk.lifecycle_timing import to_epoch_ms


class AsyncioPublishConsumerTestCase(TestCase):
    async def test_sets_lifecycle_to_transmit_ms_on_success(self):
        consumer = AsyncioPublishConsumer()

        lifecycle_started_at = utcnow() - timedelta(minutes=2)
        queue_transmit_started_at = utcnow() - timedelta(seconds=30)
        transmit_completed_at = utcnow()

        task = PublishQueueResource(
            id=ObjectId(),
            state=PublishQueueState.PENDING,
            item_id="item-1",
            item_version=1,
            headline="headline",
            publishing_action="published",
            formatted_item="formatted",
            subscriber_id=ObjectId(),
            destination=SubscriberDestination(_id="d1", name="dest", format="ninjs", delivery_type="file"),
            lifecycle_started_at=lifecycle_started_at,
            lifecycle_started_ms=to_epoch_ms(lifecycle_started_at),
        )

        queue_service = Mock()
        queue_service.update = AsyncMock()

        transmitter = Mock()
        transmitter.transmit = Mock(return_value=None)

        with patch(
            "superdesk.publish_async.consumers.asyncio_consumer.PublishQueueResource.get_service",
            return_value=queue_service,
        ):
            with patch(
                "superdesk.publish_async.consumers.asyncio_consumer.registered_transmitters", {"file": transmitter}
            ):
                with patch(
                    "superdesk.publish_async.consumers.asyncio_consumer.utcnow",
                    side_effect=[queue_transmit_started_at, transmit_completed_at],
                ):
                    result = await consumer.transmit_item(task)

        self.assertTrue(result)
        self.assertEqual(2, queue_service.update.await_count)

        first_update_args = queue_service.update.await_args_list[0].args
        self.assertEqual(task.id, first_update_args[0])
        self.assertEqual(PublishQueueState.IN_PROGRESS, first_update_args[1]["state"])
        self.assertEqual(queue_transmit_started_at, first_update_args[1]["transmit_started_at"])

        second_update_args = queue_service.update.await_args_list[1].args
        self.assertEqual(task.id, second_update_args[0])
        self.assertEqual(PublishQueueState.SUCCESS, second_update_args[1]["state"])
        self.assertEqual(transmit_completed_at, second_update_args[1]["completed_at"])
        self.assertEqual(to_epoch_ms(transmit_completed_at), second_update_args[1]["completed_ms"])

        expected_duration_ms = to_epoch_ms(transmit_completed_at) - to_epoch_ms(lifecycle_started_at)
        self.assertEqual(expected_duration_ms, second_update_args[1]["lifecycle_to_transmit_ms"])

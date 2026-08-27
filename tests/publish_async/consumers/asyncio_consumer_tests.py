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

    async def test_uses_latest_etag_when_transmitter_updated_the_queue_item(self):
        self.app.config["MAX_TRANSMIT_RETRY_ATTEMPT"] = 4
        consumer = AsyncioPublishConsumer()

        def make_task(etag, state, retry_attempt):
            return PublishQueueResource(
                id=queue_id,
                etag=etag,
                state=state,
                retry_attempt=retry_attempt,
                item_id="item-1",
                item_version=1,
                headline="headline",
                publishing_action="published",
                formatted_item="formatted",
                subscriber_id=ObjectId(),
                destination=SubscriberDestination(_id="d1", name="dest", format="ninjs", delivery_type="file"),
            )

        queue_id = ObjectId()
        task = make_task("etag-pending", PublishQueueState.PENDING, 0)
        in_progress_task = make_task("etag-in-progress", PublishQueueState.IN_PROGRESS, 0)
        # the transmitter stores an error message on the queue item, which regenerates the etag
        transmitter_updated_task = make_task("etag-from-transmitter", PublishQueueState.PENDING, 0)

        queue_service = Mock()
        queue_service.update = AsyncMock(return_value=in_progress_task)
        queue_service.find_by_id = AsyncMock(return_value=transmitter_updated_task)

        transmitter = Mock()
        transmitter.transmit = Mock(side_effect=Exception("boom"))

        with patch(
            "superdesk.publish_async.consumers.asyncio_consumer.PublishQueueResource.get_service",
            return_value=queue_service,
        ):
            with patch(
                "superdesk.publish_async.consumers.asyncio_consumer.registered_transmitters", {"file": transmitter}
            ):
                result = await consumer.transmit_item(task)

        self.assertFalse(result)
        self.assertEqual(2, queue_service.update.await_count)

        failure_update_args = queue_service.update.await_args_list[1].args
        self.assertEqual(queue_id, failure_update_args[0])
        self.assertEqual(PublishQueueState.RETRYING, failure_update_args[1]["state"])
        self.assertEqual(1, failure_update_args[1]["retry_attempt"])
        self.assertEqual("etag-from-transmitter", failure_update_args[2])
        self.assertEqual(transmitter_updated_task, failure_update_args[3])

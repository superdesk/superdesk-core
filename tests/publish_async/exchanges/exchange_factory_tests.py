from datetime import timedelta
from unittest import mock

from bson import ObjectId

from superdesk.types import (
    PublishQueueResource,
    PublishQueueState,
    SubscribersResource,
    SubscriberDestination,
    SubscriberType,
    PublishRequest,
    PublishSenderType,
)
from superdesk.publish_async import get_exchange_factory
from superdesk.publish_async.exchanges import DefaultPublishExchangeFactory
from superdesk.resource_fields import ID_FIELD
from superdesk.utc import utcnow
from superdesk.tests import TestCase


class ExchangeFactoryTestCase(TestCase):
    subscribers = [
        SubscribersResource(  # type: ignore[call-arg]
            name="subscriberA",
            subscriber_type=SubscriberType.WIRE,
            email="subscriber@a.org",
        ),
        SubscribersResource(  # type: ignore[call-arg]
            name="subscriberB",
            subscriber_type=SubscriberType.ALL,
            email="subscriber@b.org",
        ),
    ]
    queue_items: list[PublishQueueResource] = [
        PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=subscribers[0].id,
            state=PublishQueueState.PENDING,
            item_id="1",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
        PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=subscribers[1].id,
            state=PublishQueueState.PENDING,
            item_id="1",
            publish_schedule=utcnow() + timedelta(minutes=10),
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
        PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=subscribers[0].id,
            state=PublishQueueState.PENDING,
            item_id="2",
            publish_schedule=utcnow() - timedelta(minutes=10),
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
        PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(
                delivery_type="content_api",
                format="ninjs",
                config={},
                name="destination1",
            ),
            subscriber_id=subscribers[0].id,
            state=PublishQueueState.SUCCESS,
            item_id="2",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        ),
    ]
    published_items = [
        {
            "_id": ObjectId(),
            "item_id": "1",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "published",
        },
        {
            "_id": ObjectId(),
            "item_id": "2",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "scheduled",
            "operation": "publish",
            "type": "text",
            "publish_schedule": utcnow() - timedelta(minutes=5),
            "schedule_settings": {
                "utc_publish_schedule": utcnow() - timedelta(minutes=5),
                "timezone": "UTC",
                "utc_embargo": None,
            },
        },
        {
            "_id": ObjectId(),
            "item_id": "3",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "scheduled",
            "publish_schedule": utcnow() + timedelta(minutes=60),
            "schedule_settings": {
                "utc_publish_schedule": utcnow() + timedelta(minutes=60),
                "timezone": "UTC",
                "utc_embargo": None,
            },
        },
    ]

    async def test_get_scheduled_items(self):
        self.app.data.insert("published", self.published_items)
        items = await get_exchange_factory().get_pending_or_scheduled_content_for_publishing()
        self.assertEqual(2, len(items))
        ids = [item[ID_FIELD] for item in items]
        self.assertNotIn(self.published_items[2][ID_FIELD], ids)

    @mock.patch("superdesk.publish_async.exchanges.DefaultPublishExchangeFactory.send")
    async def test_process_scheduled_tasks(self, mock_send):
        item = self.published_items[1]
        self.app.data.insert("published", [item])
        await get_exchange_factory().send_scheduled_or_pending_content()

        mock_send.assert_called_with(
            PublishRequest(
                item=item,
                item_id=item["item_id"],
                item_type="text",
                operation="publish",
                published_state="scheduled",
                sender_type=PublishSenderType.INTERNAL,
                publish_to_content_api=True,
            )
        )

    async def test_get_task_subscriber_ids(self):
        await SubscribersResource.get_service().create(self.subscribers)
        await PublishQueueResource.get_service().create(self.queue_items)
        subscriber_ids = await get_exchange_factory().get_task_subscriber_ids()
        self.assertEqual(sorted(subscriber_ids), [self.subscribers[0].id, self.subscribers[1].id])

    async def test_get_subscriber_tasks(self):
        await SubscribersResource.get_service().create(self.subscribers)
        await PublishQueueResource.get_service().create(self.queue_items)
        tasks = await get_exchange_factory().get_subscriber_tasks(self.subscribers[0].id)
        task_ids = [task.id for task in tasks]
        self.assertEqual(sorted(task_ids), [self.queue_items[0].id, self.queue_items[2].id])

        tasks = await get_exchange_factory().get_subscriber_tasks(self.subscribers[1].id)
        task_ids = [task.id for task in tasks]
        self.assertEqual(sorted(task_ids), [self.queue_items[1].id])

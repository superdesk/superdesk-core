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

    async def test_create_skips_duplicate_queue_items(self):
        await SubscribersResource.get_service().create(self.subscribers)

        queue_item = PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=self.subscribers[0].id,
            state=PublishQueueState.PENDING,
            item_id="duplicate-item",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        )
        duplicate_queue_item = PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=self.subscribers[0].id,
            state=PublishQueueState.PENDING,
            item_id="duplicate-item",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        )

        await PublishQueueResource.get_service().create([queue_item, duplicate_queue_item])

        queue_items = [queue async for queue in PublishQueueResource.get_service().get_all()]
        self.assertEqual(1, len(queue_items))

        # Ensure duplicates are also skipped when the duplicate arrives in a later request
        later_duplicate = PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="destination1"),
            subscriber_id=self.subscribers[0].id,
            state=PublishQueueState.PENDING,
            item_id="duplicate-item",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        )
        await PublishQueueResource.get_service().create([later_duplicate])
        queue_items = [queue async for queue in PublishQueueResource.get_service().get_all()]
        self.assertEqual(1, len(queue_items))

    async def test_stale_routing_items_are_included_in_subscriber_tasks(self):
        """
        Queue items stuck in ``routing`` state older than 5 minutes should be
        returned by get_subscriber_tasks() so the background worker retries them.
        A freshly-created ``routing`` item (within the lock TTL window) must NOT
        be returned yet.
        """
        await SubscribersResource.get_service().create(self.subscribers)

        stale_routing = PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="d1"),
            subscriber_id=self.subscribers[0].id,
            state=PublishQueueState.ROUTING,
            item_id="stale-routing",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        )
        fresh_routing = PublishQueueResource(  # type: ignore[call-arg]
            destination=SubscriberDestination(format="ninjs", delivery_type="ftp", config={}, name="d1"),
            subscriber_id=self.subscribers[0].id,
            state=PublishQueueState.ROUTING,
            item_id="fresh-routing",
            publishing_action="publish",
            item_version=1,
            formatted_item="",
        )

        await PublishQueueResource.get_service().create([stale_routing, fresh_routing])

        # Back-date the stale item so it falls outside the 5-minute lock window
        await PublishQueueResource.get_service().update(
            stale_routing.id,
            {"_created": utcnow() - timedelta(minutes=6)},
        )

        tasks = await get_exchange_factory().get_subscriber_tasks(self.subscribers[0].id)
        task_ids = [task.id for task in tasks]

        self.assertIn(stale_routing.id, task_ids, "stale routing item should be picked up for retry")
        self.assertNotIn(fresh_routing.id, task_ids, "fresh routing item should not be picked up yet")

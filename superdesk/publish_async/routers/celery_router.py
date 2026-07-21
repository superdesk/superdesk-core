from bson import ObjectId
import logging
from quart_babel import gettext
from superdesk.types import PublishQueueResource, SubscribersResource
from superdesk.celery_app import celery
from superdesk.errors import SuperdeskApiError
from superdesk.publish_async import get_exchange_factory

from .asyncio_router import AsyncioPublishRouter
from ..utils import ContentApiSubscriber


logger = logging.getLogger(__name__)


class CeleryPublishRouter(AsyncioPublishRouter):
    """
    Handles the routing of tasks to a consumer using Celery.

    The CeleryPublishRouter class is designed to work as a publish router specifically
    for integrating with the Celery task distribution system. This class leverages
    an asynchronous approach for sending tasks to a consumer via Celery. It inherits
    functionality from AsyncioPublishRouter and specializes it for Celery-related use cases.
    """

    name: str = "celery"

    async def send_tasks_to_consumer(self, subscriber: SubscribersResource, tasks: list[PublishQueueResource]) -> None:
        """
        Send multiple tasks to a consumer based on a given subscriber.

        This asynchronous function retrieves a consumer associated with the provided
        subscriber and enqueues tasks to be sent to that consumer. The tasks are
        defined as a list of PublishQueueResource instances. Each task's identifier
        is sent to the consumer for processing.

        :param subscriber: The subscriber resource associated with the consumer.
        :param tasks: A list of task instances to be sent to the consumer.
        """

        consumer = get_exchange_factory().get_subscriber_consumer(subscriber)
        task_ids = [task.id for task in tasks]
        try:
            await send_task_to_consumer.apply_async(  # type: ignore[attr-defined]
                args=[
                    consumer.name,
                    subscriber.id,
                    task_ids,
                ]
            )
        except Exception:
            logger.exception(
                "Failed to enqueue publish tasks to celery consumer",
                extra=dict(
                    subscriber_id=subscriber.id,
                    consumer_name=consumer.name,
                    task_ids=[str(task_id) for task_id in task_ids],
                    queue_item_ids=[task.item_id for task in tasks],
                ),
            )
            raise


@celery.task(soft_time_limit=600)
async def send_task_to_consumer(consumer_name: str, subscriber_id: ObjectId, task_ids: list[ObjectId]) -> None:
    """
    An asynchronous function to send tasks to a specified consumer by identifying the subscriber
    and tasks using their respective IDs, then delegating the processing to the consumer.

    :param consumer_name: The name of the consumer to which the tasks are sent.
    :param subscriber_id: The unique identifier of the subscriber.
    :param task_ids: A list of task unique identifiers to be processed.
    :raises SuperdeskApiError: Raised with a badRequestError if the subscriber is not found.
    """

    consumer = get_exchange_factory().get_consumer(consumer_name)
    subscriber = (
        ContentApiSubscriber
        if subscriber_id == ContentApiSubscriber.id
        else await SubscribersResource.get_service().find_by_id(subscriber_id)
    )

    if subscriber is None:
        raise SuperdeskApiError.badRequestError(gettext(f"Subscriber {subscriber_id} not found."))

    tasks = await PublishQueueResource.get_service().find_by_ids(task_ids)
    await consumer.process_tasks(subscriber, tasks)

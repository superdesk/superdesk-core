from bson import ObjectId
from quart_babel import gettext
from superdesk.types import PublishQueueResource, SubscribersResource
from superdesk.celery_app import celery
from superdesk.errors import SuperdeskApiError
from superdesk.publish_async import get_exchange_factory

from .asyncio_router import AsyncioPublishRouter


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
        await send_task_to_consumer.apply_async(
            args=[
                consumer.name,
                subscriber.id,
                [task.id for task in tasks],
            ]
        )


@celery.task(soft_time_limit=600, expires=10)
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

    subscriber = await SubscribersResource.get_service().find_by_id(subscriber_id)
    if subscriber is None:
        raise SuperdeskApiError.badRequestError(gettext(f"Subscriber {subscriber_id} not found."))

    tasks = await PublishQueueResource.get_service().find_by_ids(task_ids)
    await consumer.process_tasks(subscriber, tasks)

import logging

from bson import ObjectId

from superdesk.types import PublishQueueResource, SubscribersResource
from superdesk.celery_app import celery
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock

from ..utils import get_high_priority_celery_queue
from .asyncio_consumer import AsyncioPublishConsumer


logger = logging.getLogger(__name__)


class CeleryPublishConsumer(AsyncioPublishConsumer):
    """
    Handles the consumption and processing of tasks using Celery in an asyncio-based
    publishing consumer.

    This class is responsible for coordinating and ensuring the transmission of tasks
    utilizing Celery's asynchronous task queue system. It ensures no concurrent task
    execution for the same subscriber while managing the process lifecycle, including
    locking and unlocking resources.

    Attributes:
        Inherits all attributes from AsyncioPublishConsumer.
    """

    name: str = "celery"

    async def process_tasks(self, subscriber: SubscribersResource, tasks: list[PublishQueueResource]) -> None:
        """
        An asynchronous method to process and transmit tasks for a given subscriber.

        This method processes the provided tasks by acquiring a lock to ensure that
        multiple tasks for the same subscriber do not overlap. For each task, it
        schedules its execution in a high-priority Celery queue based on the task's
        priority. After processing, the lock is released.

        :param subscriber: The subscriber resource for which the tasks are being processed.
        :param tasks: A list of tasks to be processed and transmitted.
        """

        # We assume all tasks come from the same subscriber
        lock_name = get_lock_id("Subscriber", "Transmit", str(subscriber.id))
        if not lock(lock_name, expire=610):
            logger.info(f"Task: {lock_name} is already running.")
            return

        try:
            for task in tasks:
                await transmit_item.apply_async(args=[task.id], queue=get_high_priority_celery_queue(task.priority))
        finally:
            logger.debug(f"unlock {lock_name}")
            unlock(lock_name)


@celery.task(soft_time_limit=600, expires=10)
async def transmit_subscriber_items(subscriber_id: ObjectId, task_ids: list[ObjectId]) -> None:
    """
    This asynchronous function handles the transmission of subscriber items by processing
    a list of task IDs. It utilizes a locking mechanism to ensure that only one instance
    of this task for a given subscriber ID is executed at a time. Tasks are retrieved,
    checked for validity, and enqueued for further transmission via a high-priority
    Celery queue.

    :param subscriber_id: The unique identifier of the subscriber for whom tasks are being transmitted.
    :param task_ids: A list of unique task identifiers to be processed and transmitted.
    """

    lock_name = get_lock_id("Subscriber", "Transmit", str(subscriber_id))

    if not lock(lock_name, expire=610):
        logger.info(f"Task: {lock_name} is already running.")
        return

    try:
        task_service = PublishQueueResource.get_service()
        for task_id in task_ids:
            task = await task_service.find_by_id(task_id)
            if task is None:
                logger.exception("Task not found.", extra=dict(task_id=task_id))
                continue
            await transmit_item.apply_async(args=[task.id], queue=get_high_priority_celery_queue(task.priority))
    finally:
        logger.debug(f"unlock {lock_name}")
        unlock(lock_name)


@celery.task(soft_time_limit=300)
async def transmit_item(task_id: ObjectId) -> None:
    """
    An asynchronous function to transmit an item from the queue to a consumer
    using a locking mechanism to prevent simultaneous execution of tasks with
    the same identifier.

    :param task_id: The unique identifier of the task to be transmitted.
    :raises celery.exceptions.SoftTimeLimitExceeded: If the task does not complete within its soft time limit.

    .. note::
        This function uses a locking mechanism to ensure that only one instance
        of a task is running at any given time. If the lock cannot be acquired,
        the function will log a message and return early.
    """

    consumer = CeleryPublishConsumer()
    lock_name = get_lock_id("Transmit", str(task_id))
    if not lock(lock_name, expire=310):
        logger.info(f"Task: {lock_name} is already running.")
        return

    try:
        task = await PublishQueueResource.get_service().find_by_id(task_id)
        if task is None:
            logger.exception("Task not found.", extra=dict(task_id=task_id))
            return
        await consumer.transmit_item(task)
    finally:
        logger.debug(f"unlock {lock_name}")
        unlock(lock_name, remove=True)

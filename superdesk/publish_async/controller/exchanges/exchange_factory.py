import logging

from bson import ObjectId

from superdesk.core import get_config
from superdesk.types import PublishQueueResource, PublishQueueState, SubscribersResource, PublishConsumer
from superdesk.utc import utcnow
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock, is_locked
from superdesk.profiling import ProfileManager
from superdesk.celery_app import celery

from ..utils import get_high_priority_celery_queue
from ..consumers import AsyncioPublishConsumer, CeleryPublishConsumer


logger = logging.getLogger(__name__)


class ExchangeFactory:
    """
    Factory class for creating various types of consumers and managing tasks.

    This class provides factory methods to create consumer instances based on
    different configurations, as well as methods to handle asynchronous tasks.
    It supports determining consumer types dynamically based on input parameters
    and ensures efficient processing of article transmission tasks with proper
    locking and retry logic.
    """

    @classmethod
    def get_subscriber_consumer(cls, subscriber: SubscribersResource) -> PublishConsumer:
        """
        Create and return a specific type of consumer based on the subscriber's configuration.

        This class method determines whether to create an asynchronous or a celery-based
        publish consumer depending on whether the subscriber supports asynchronous operations.

        Parameters:
        subscriber (SubscribersResource): A subscriber resource containing configuration
                                          details, including whether asynchronous operations
                                          are allowed.

        Returns:
        PublishConsumer: An instance of PublishConsumer, either asynchronous or celery-based.
        """
        return AsyncioPublishConsumer() if subscriber.is_async else CeleryPublishConsumer()

    @classmethod
    async def process_pending_tasks(cls):
        """
        An asynchronous class method to process pending tasks for transmitting articles.
        This method takes care of handling locks, task prioritization, and retry logic to ensure
        tasks are executed in the correct order while avoiding duplicate executions. It uses
        Celery to queue tasks for asynchronous processing efficiently.

        Raises:
            Exception: If any exception occurs during the process, it is logged for debugging purposes.
        """

        with ProfileManager("publish:transmit"):
            lock_name = get_lock_id("Transmit", "Articles")
            if not lock(lock_name, expire=1810):
                logger.info("Task: %s is already running.", lock_name)
                return

            try:
                for priority in [True, False]:  # top priority first
                    for retries in [False, True]:  # first publish pending, retries after
                        subscriber_ids = await _get_task_subscriber_ids(retries, priority)
                        for subscriber_id in subscriber_ids:
                            sub_lock_name = get_lock_id("Subscriber", "Transmit", str(subscriber_id))
                            if is_locked(sub_lock_name):
                                logger.info("Task: %s is already running.", sub_lock_name)
                                continue

                            await transmit_subscriber_items.apply_async(
                                args=[subscriber_id],
                                kwargs={"retries": retries, "priority": priority},
                                queue=get_high_priority_celery_queue(priority),
                            )

            except Exception:
                logger.exception(f"Task: {lock_name} failed.")
            finally:
                logger.debug(f"unlock {lock_name}")
                unlock(lock_name)


@celery.task(soft_time_limit=600, expires=10)
async def transmit_subscriber_items(
    subscriber_id: ObjectId, retries: bool = False, priority: bool | None = None
) -> None:
    """
    Asynchronously transmits tasks associated with a subscriber to a designated consumer.

    Fetches subscriber information and retrieves tasks that match the specified
    criteria. If valid tasks are found, they are transmitted to the appropriate
    subscriber consumer for further processing. Logs relevant information and errors
    during the operation execution.

    Args:
        subscriber_id: The unique identifier of the subscriber.
        retries: A flag indicating whether previously failed tasks should be retried.
        priority: An optional parameter that specifies whether tasks of a certain
                  priority should be processed.

    Raises:
        soft_time_limit: Limits task execution to a maximum of 600 seconds.
        expires: Restricts task availability to 10 seconds after scheduling.
    """
    subscriber = await SubscribersResource.get_service().find_by_id(subscriber_id)
    if subscriber is None:
        logger.exception(f"Subscriber {subscriber_id} not found.")
        return

    tasks = await _get_subscriber_tasks(subscriber_id, retries, priority)
    if len(tasks) == 0:
        logger.info(f"No tasks found for subscriber {subscriber_id}")
        return

    await ExchangeFactory().get_subscriber_consumer(subscriber).process_tasks(subscriber, tasks)


def _get_queue_lookup(retries: bool = False, priority: bool | None = None) -> dict:
    """
    Constructs a query to filter the publish queue based on retries and priority
    parameters.

    The function generates a MongoDB query for fetching records from a publish
    queue based on their state, retry attempt time, and priority. It is designed
    to distinguish between pending and retrying states, optionally filtering by
    priority.

    Args:
        retries (bool): Indicates whether to filter for retrying states.
        priority (bool | None): Optionally filters queue items by priority.
            If None, it matches records where the priority attribute is not set
            or is equal to True.

    Returns:
        dict: A dictionary representing the MongoDB query with conditional
        predicates based on the provided arguments.
    """
    priority_lookup = {"priority": priority if priority else {"$ne": True}}
    if retries:
        return {
            "$and": [
                {"state": PublishQueueState.RETRYING},
                {"next_retry_attempt_at": {"$lte": utcnow()}},
                priority_lookup,
            ]
        }
    return {
        "$and": [
            {"state": PublishQueueState.PENDING},
            priority_lookup,
        ]
    }


async def _get_task_subscriber_ids(retries: bool = False, priority: bool | None = None) -> list[ObjectId]:
    """
    Retrieve the subscriber IDs of tasks based on the queue lookup criteria.

    This function asynchronously retrieves a list of `subscriber_id` values by
    performing a distinct query on the `PublishQueueResource` service. The query
    parameters are determined by the specified retry and priority conditions.

    Parameters:
        retries (bool): Indicates whether the query should include tasks flagged
            for retry.
        priority (bool | None): Specifies the priority level to filter by. If None,
            priority filtering is not applied.

    Returns:
        list[ObjectId]: A list of unique subscriber IDs matching the specified
        query conditions.
    """
    lookup = _get_queue_lookup(retries, priority)
    return await PublishQueueResource.get_service().mongo_async.distinct("subscriber_id", lookup)


async def _get_subscriber_tasks(
    subscriber_id: ObjectId, retries: bool = False, priority: bool | None = None
) -> list[PublishQueueResource]:
    """
    Asynchronous function to retrieve subscriber tasks based on the provided lookup filters such as subscriber
    ID, retry status, and priority. This function interacts with the PublishQueueResource service instance
    to query the matching tasks and returns them in a list format. The query results are limited by the
    configured maximum transmit query limit and ordered by creation time and published sequence number.

    Args:
        subscriber_id (ObjectId): The unique identifier of the subscriber whose tasks are to be retrieved.
        retries (bool, optional): A flag to indicate whether to include tasks eligible for retries.
        priority (bool | None, optional): If specified, filters the tasks based on priority.

    Returns:
        list[PublishQueueResource]: A list of PublishQueueResource objects matching the applied filters.
    """
    lookup = _get_queue_lookup(retries, priority)
    lookup["$and"].append({"subscriber_id": subscriber_id})
    return await (
        await PublishQueueResource.get_service().find(
            lookup,
            max_results=get_config(int, "MAX_TRANSMIT_QUERY_LIMIT"),  # limit per subscriber now,
            sort=[("_created", 1), ("published_seq_num", 1)],
        )
    ).to_list()

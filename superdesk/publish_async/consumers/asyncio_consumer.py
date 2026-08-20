from typing import Awaitable
import logging
from inspect import isawaitable
from asyncio import gather
from datetime import timedelta

from superdesk.types import PublishQueueResource, PublishQueueState, SubscribersResource, PublishConsumer
from superdesk.core import get_config
from superdesk.errors import PublishHTTPPushClientError
from superdesk.utc import utcnow
from superdesk.resource_fields import LAST_UPDATED
from superdesk.publish import registered_transmitters
from superdesk.publish_async.utils import compute_retry_timeout_minutes
from superdesk.lifecycle_timing import duration_ms, to_epoch_ms, duration_ms_from_epoch

logger = logging.getLogger(__name__)


class AsyncioPublishConsumer(PublishConsumer):
    """
    Represents an asyncio-based publish consumer that extends the PublishConsumer class.

    This class provides functionality for processing and transmitting publishing queue tasks
    asynchronously. It works in conjunction with specific subscriber resources and queue
    resources. The implementation focuses on handling the states and transitions associated
    with the tasks and ensures robust error handling and retries for failed transmissions.
    """

    name: str = "asyncio"

    async def process_tasks(self, subscriber: SubscribersResource, tasks: list[PublishQueueResource]) -> None:
        """
        Processes a list of publishing tasks by attempting to transmit each item asynchronously and logs any errors that occur.

        :param subscriber: Represents the subscriber resource.
        :param tasks: A list of publishing queue resources to be processed.
        """
        task_results: list[Awaitable[bool]] = [self.transmit_item(task) for task in tasks]
        for index, result in enumerate(await gather(*task_results, return_exceptions=True)):
            task = tasks[index]
            if result is not True:
                logger.debug(f"got error transmitting item {task.id}")

    async def transmit_item(self, task: PublishQueueResource) -> bool:
        """
        Handles the transmission of an item from the publish queue.

        This method manages the state transitions for the item being processed, including
        updating the state of the publish queue resource, selecting the appropriate
        transmitter for the item's destination delivery type, and handling success or
        failure scenarios during transmission.

        If the transmission is successful, the task's state is updated, and processing is
        completed. In case of failures, it attempts to handle retries based on the
        configured maximum retry attempts and delay. Errors encountered during the process
        are logged, and the task state is updated appropriately. The method ensures that
        unrecoverable errors halt further processing to avoid prolonged blocking of resources.

        :param task: The publish queue resource to be transmitted. Contains information
            such as state, destination, item details, retry attempts, and more.
        :return: A boolean indicating whether the transmission was successful.
        :raises Exception: If unrecoverable errors occur during the transmission process or while
            updating the task state. Such errors are raised to halt further processing.
        """
        log_msg = (
            f"_id: {task.id} item_id: {task.item_id} state: {task.state} "
            f"item_version: {task.item_version} headline: {task.headline}"
        )
        log_extra = dict(
            task_id=task.id,
            task_state=task.state,
            item_id=task.item_id,
            item_version=task.item_version,
            item_headline=task.headline,
        )
        if task.state not in [PublishQueueState.ROUTING, PublishQueueState.PENDING, PublishQueueState.RETRYING]:
            logger.warning(
                "Transmit State is not pending/retrying for queue item "
                "(task_id=%s item_id=%s item_version=%s state=%s)",
                task.id,
                task.item_id,
                task.item_version,
                task.state,
                extra=log_extra,
            )
            return False
        elif task.destination is None:
            logger.error("Destination not defined in queue item", extra=log_extra)
            return False

        # Every update regenerates the item's etag, so the stored version is tracked separately
        # from `task`: each state update below is checked against the etag it is given and fails
        # with a 412 once that etag is no longer the one held in the database.
        current = task

        try:
            # Update the status of the task to in-progress
            task_update = {"state": PublishQueueState.IN_PROGRESS, "transmit_started_at": utcnow()}
            current = await PublishQueueResource.get_service().update(task.id, task_update, current.etag, current)
            logger.info(f"Transmitting queue item {log_msg}")

            try:
                transmitter = registered_transmitters[task.destination.delivery_type]
            except KeyError:
                print(task.destination.delivery_type not in registered_transmitters)
                raise

            response = transmitter.transmit(task.to_dict(context={"use_objectid": True}))
            if isawaitable(response):
                # TODO-ASYNC: Convert transmitters to use asyncio network calls
                # otherwise it will halt the processing of other transmission requests
                # while waiting for network responses
                await response

            completed_now = utcnow(microseconds=True)
            completed_at = completed_now.replace(microsecond=0)
            completed_ms: int = to_epoch_ms(completed_now)
            success_update: dict[str, object] = {
                "state": PublishQueueState.SUCCESS,
                "completed_at": completed_at,
                "completed_ms": completed_ms,
            }
            if isinstance(task.lifecycle_started_ms, int):
                success_update["lifecycle_to_transmit_ms"] = duration_ms_from_epoch(
                    task.lifecycle_started_ms, completed_ms
                )
            elif task.lifecycle_started_at:
                success_update["lifecycle_to_transmit_ms"] = duration_ms(task.lifecycle_started_at, completed_now)

            await PublishQueueResource.get_service().update(task.id, success_update, current.etag, current)
            logger.info(f"Transmit completed for queue item {log_msg}")

            return True
        except Exception as e:
            logger.exception("Failed to transmit queue item", extra=log_extra)

            max_retry_attempt = get_config(int, "MAX_TRANSMIT_RETRY_ATTEMPT")
            initial_retry_delay_minutes = get_config(
                int,
                "TRANSMIT_RETRY_INITIAL_DELAY_MINUTES",
                get_config(int, "TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES", 1),
            )
            max_retry_delay_minutes = get_config(
                int,
                "TRANSMIT_RETRY_MAX_DELAY_MINUTES",
                get_config(int, "MAX_TRANSMIT_RETRY_DELAY_MINUTES", 120),
            )
            try:
                retry_attempt = task.retry_attempt or 0
                timeout_minutes = compute_retry_timeout_minutes(
                    retry_attempt,
                    initial_retry_delay_minutes,
                    max_retry_delay_minutes,
                )
                updates: dict[str, object] = {LAST_UPDATED: utcnow()}

                if task.retry_attempt < max_retry_attempt and not isinstance(e, PublishHTTPPushClientError):
                    updates.update(
                        {
                            "retry_attempt": task.retry_attempt + 1,
                            "state": PublishQueueState.RETRYING,
                            "next_retry_attempt_at": utcnow() + timedelta(minutes=timeout_minutes),
                        }
                    )
                else:
                    updates["state"] = PublishQueueState.FAILED

                await PublishQueueResource.get_service().update(task.id, updates, current.etag, current)
                return False
            except Exception:
                logger.error("Failed to set the state for failed publish queue item.", extra=log_extra)

            # raise to stop transmitting items and free worker, in case there is some error
            # it's probably network related so trying more items now will probably only block
            # for longer time
            logger.debug(f"Got error. {log_msg}")
            raise

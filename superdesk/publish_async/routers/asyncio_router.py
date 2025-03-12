from typing import Awaitable
import logging
from asyncio import as_completed
from bson import ObjectId

from superdesk.types import (
    PublishExchangeRouter,
    PublishRequest,
    PublishRequestResponse,
    PublishQueueResource,
    SubscribersResource,
)
from superdesk.publish_async import get_exchange_factory
from superdesk.publish_async.publish_cache import PublishCache

from ..utils import ContentApiSubscriber


logger = logging.getLogger(__name__)


class AsyncioPublishRouter(PublishExchangeRouter):
    """
    Handles asynchronous routing of publishing tasks to the appropriate consumers.

    The AsyncioPublishRouter is responsible for taking publishing tasks, grouping
    them by their intended subscribers, and dispatching them asynchronously to the
    appropriate consumers. This class utilizes asyncio to facilitate concurrent
    processing of tasks and ensures efficient handling of the routing process. It
    integrates with underlying subscriber and consumer components to execute the
    routing logic.
    """

    name: str = "asyncio"

    async def route_tasks_to_consumers(
        self, request: PublishRequest, response: PublishRequestResponse, tasks: list[PublishQueueResource]
    ) -> None:
        """
        Async route_tasks_to_consumers(request: PublishRequest, response: PublishRequestResponse, tasks: list[PublishQueueResource]) -> None

        Summary:
        Asynchronously routes a list of publish tasks to corresponding subscribers via their
        respective PublishConsumer(s). This function first initializes the PublishCache,
        groups tasks by their subscriber, and sends them to the appropriate consumer.
        It keeps track of the success or failure of these tasks and updates the response
        object accordingly.

        :param request: The request object containing data necessary for routing tasks.
        :param response: The response object to be updated with the routing outcome.
        :param tasks: A list of tasks to be routed to the respective consumers.
        """

        # Now send the tasks to the PublishConsumer(s)

        await PublishCache.init()
        publish_tasks: list[Awaitable[None]] = []

        for subscriber, tasks in self.group_tasks_by_subscriber(request, tasks):
            publish_tasks.append(self.send_tasks_to_consumer(subscriber, tasks))

        if publish_tasks:
            failed = 0
            for task in as_completed(publish_tasks):
                try:
                    await task
                except Exception:
                    failed += 1

            if not failed:
                response.routed = True

    def group_tasks_by_subscriber(
        self, request: PublishRequest, tasks: list[PublishQueueResource]
    ) -> list[tuple[SubscribersResource, list[PublishQueueResource]]]:
        """
        Groups tasks by their associated subscriber and consumer.

        This function processes a list of tasks, associates them with their respective
        subscribers and consumers from the cache, and returns the result as a list
        of tuples. Each tuple consists of a subscriber resource and a list of
        associated tasks. If a task is designated for the content API, it is grouped
        separately and handled as a single unit for all subscribers.

        :param request: The publish request which contains the item and additional information relevant
            for the task and subscriber grouping process.
        :param tasks: A list of tasks to be grouped by their associated subscribers.
        :return: A list of tuples. Each tuple contains a subscriber resource and a list
            of tasks associated with that subscriber.
        """

        cache = PublishCache.get()
        subscriber_tasks: dict[ObjectId, tuple[SubscribersResource, list[PublishQueueResource]]] = {}
        content_api_task: PublishQueueResource | None = None

        # Group Tasks with their associated Subscriber and Consumer
        for task in tasks:
            subscriber = cache.subscribers.get(task.subscriber_id)
            if not subscriber:
                logger.warning(f"Subscriber {task.subscriber_id} not found.")
                continue

            if task.is_content_api:
                # We skip this one, as we'll publish to the Content API for all Subscribers in one step
                if content_api_task is None:
                    content_api_task = task
                continue

            subscriber_tasks.setdefault(subscriber.id, (subscriber, []))[1].append(task)

        if content_api_task:
            content_api_task.item = request.item
            subscriber_tasks[ContentApiSubscriber.id] = (ContentApiSubscriber, [content_api_task])

        return list(subscriber_tasks.values())

    async def send_tasks_to_consumer(self, subscriber: SubscribersResource, tasks: list[PublishQueueResource]) -> None:
        """
        This method sends a list of tasks to the specified consumer for processing.
        It utilizes the subscriber to fetch the appropriate consumer instance
        and delegates task processing to the consumer. In case of an error during
        processing, the method logs the exception.

        :param subscriber: The subscriber resource used to fetch the consumer.
        :param tasks: A list of tasks to be processed.
        """

        try:
            consumer = get_exchange_factory().get_subscriber_consumer(subscriber)
            await consumer.process_tasks(subscriber, tasks)
        except Exception:
            logger.exception(f"Failed to process tasks for subscriber {subscriber.id}")

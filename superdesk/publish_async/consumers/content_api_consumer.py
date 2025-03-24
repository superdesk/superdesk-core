import logging

from superdesk.types import PublishQueueResource, SubscribersResource, PublishConsumer
from superdesk.resource_fields import ID_FIELD
from superdesk import get_resource_service
from superdesk.publish_async.publish_cache import PublishCache


logger = logging.getLogger(__name__)


class ContentApiPublishConsumer(PublishConsumer):
    """
    Handles tasks related to publishing items to the Content API.

    This class is responsible for consuming publishing tasks from a queue and
    processing them by publishing the corresponding items to the Content API. It
    inherits from the `PublishConsumer` base class. The primary use of this class
    is to facilitate seamless publishing of content to the API, handling resources
    and ensuring proper subscriber management.
    """

    name: str = "content_api"

    async def process_tasks(self, subscriber: SubscribersResource, tasks: list[PublishQueueResource]) -> None:
        """
        Processes a list of tasks for publishing content to the Content API.

        This method iterates over the provided tasks, retrieves corresponding subscriber
        information from cache, and attempts to publish the specified content item to the
        subscribers via the ContentAPI. If no tasks are provided or the first task does not
        contain a valid content item, a warning is logged and the method returns without
        performing any publishing actions. If an error occurs during the publishing process,
        an exception is logged containing details about the failed publishing operation.

        :param subscriber: Represents the subscriber resource.
        :param tasks: A list of publishing queue resources to be processed.
        """

        item = tasks[0].item if len(tasks) else None
        if not item:
            logger.warning("ContentAPI item not found in provided tasks")
            return

        subscriber_ids = [task.subscriber_id for task in tasks]
        cache = await PublishCache.init()
        subscribers = [
            cache.subscribers[subscriber_id].to_dict()
            for subscriber_id in subscriber_ids
            if cache.subscribers.get(subscriber_id)
        ]
        try:
            get_resource_service("content_api").publish(item, subscribers)
        except Exception:
            logger.exception(
                "Failed to queue item to API",
                extra=dict(
                    item_id=item[ID_FIELD],
                    operation=tasks[0].publishing_action,
                ),
            )

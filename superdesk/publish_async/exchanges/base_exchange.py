import logging

from superdesk.core import get_config
from superdesk.types import PublishRequest, PublishRequestResponse, PublishExchange, PublishQueueResource
from superdesk.resource_fields import ID_FIELD
from superdesk.notification import push_notification
from superdesk.publish_async.publish_cache import PublishCache

from apps.archive.common import get_user


logger = logging.getLogger(__name__)


class BasicPublishExchange(PublishExchange):
    """
    BasicPublishExchange class.

    This class extends PublishExchange and provides functionality for publishing
    content where it handles subscribers, tasks, routing, and formatting. It serves
    as a connecting layer to manage publish-related activities such as formatting
    notifications and routing tasks to appropriate consumers.
    """

    name: str = "default"

    async def send(self, request: PublishRequest) -> PublishRequestResponse:
        """
        Handles sending of publication requests to subscribers, processes tasks for routing, and manages
        notifications for formatted and non-formatted requests. Ensures exchange configuration is set for
        all tasks and performs routing. Logs an error or informational message if the publish queue target
        media type is not defined and no tasks are routed.

        :param request:The publication request containing the details for publishing.
        :return:The response object that contains the result of the publication processing and routing.
        """

        response = PublishRequestResponse()
        await PublishCache.init()
        await self.filter_subscribers(request, response)
        tasks, no_formatters = await self.get_tasks(request, response)

        # Store this exchange config with all the Tasks,
        # So it can be used in future to retrieve the exchange that manages this task
        exchange_config = self.get_exchange_config()
        for task in tasks:
            task.exchange = exchange_config

        self._push_formatter_notification(request, no_formatters)
        await self.route_tasks(request, response, tasks)

        if not request.target_media_type and not response.routed:
            level = logging.INFO
            if get_config(bool, "PUBLISH_NOT_QUEUED_ERROR") and not get_config(bool, "SUPERDESK_TESTING"):
                level = logging.ERROR

            logger.log(
                level, f"Nothing is saved to publish queue for story: {request.item_id} for action: {request.operation}"
            )

        return response

    async def filter_subscribers(self, request: PublishRequest, response: PublishRequestResponse) -> None:
        """
        Filters subscribers based on the provided request details.

        This method applies a filtering mechanism to determine suitable subscribers
        by utilizing the provided request and response data. It delegates the actual
        filtering logic to an internal filter instance, ensuring that only relevant
        subscribers are identified.

        :param request: The publication request containing the details for publishing.
        :param response: The publish request response object
        """

        await self._filter.filter_subscribers(request, response)

    async def get_tasks(
        self, request: PublishRequest, response: PublishRequestResponse
    ) -> tuple[list[PublishQueueResource], list[str]]:
        """
        Retrieves tasks from a given request and response through an asynchronous operation.

        This method uses a formatter to extract and process tasks from the provided
        request and response objects.

        :param request: The publication request containing the details for publishing.
        :param response: The publish request response object
        :return: A tuple containing a list of PublishQueueResource objects representing
            the tasks and a list of strings representing additional information or results.
        """

        return await self._formatter.get_request_tasks(request, response)

    async def route_tasks(
        self, request: PublishRequest, response: PublishRequestResponse, tasks: list[PublishQueueResource]
    ) -> None:
        """
        Route tasks to appropriate consumers as defined by the routing logic of the router.

        This method is responsible for handling the task distribution by delegating
        them to specific consumers based on the details provided in the request,
        response, and the intended tasks. It ensures that the tasks are routed
        efficiently and correctly without returning any value.

        :param request: The publication request containing the details for publishing.
        :param response: The publish request response object
        :param tasks: A list of tasks to be routed to the respective consumers.
        """

        await self._router.route_tasks_to_consumers(request, response, tasks)

    def _push_formatter_notification(self, request: PublishRequest, no_formatters: list[str]):
        """
        Pushes a notification about missing formatters for the specified publish request.

        This method is used to notify the user about the items that do not have the correct formatters
        specified during a publish request operation.

        :param request: The publication request containing the details for publishing.
        :param no_formatters: A list of formatter names that are missing or incorrect for the item in the publish request.
        """

        if not no_formatters:
            return

        user = get_user()
        push_notification(
            "item:publish:wrong:format",
            item=str(request.item_id),
            unique_name=request.item.get("unique_name"),
            desk=str(request.item.get("task", {}).get("desk", "")),
            user=str(user.get(ID_FIELD, "")),
            formats=no_formatters,
        )

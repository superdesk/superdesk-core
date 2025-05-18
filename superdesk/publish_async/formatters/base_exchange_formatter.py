import logging
from inspect import isawaitable
from io import BytesIO
from copy import deepcopy

from bson import ObjectId
from quart_babel import gettext

from superdesk.core import get_current_app

from superdesk.types import (
    PublishExchangeFormatter,
    ContentType,
    SubscribersResource,
    PublishRequest,
    PublishRequestResponse,
    PublishQueueResource,
    PublishQueueState,
    SubscriberDestination,
)
from superdesk import get_resource_service
from superdesk.resource_fields import ID_FIELD, ITEM_TYPE, ASSOCIATIONS, VERSION
from superdesk.metadata.item import PUBLISH_SCHEDULE
from superdesk.metadata.packages import GROUPS, GROUP_ID, REFS, RESIDREF, ROOT_GROUP
from superdesk.publish import PUBLISHED_IN_PACKAGE
from superdesk.errors import SuperdeskPublishError
from superdesk.publish_async.publish_cache import PublishCache
from superdesk.publish_async.utils import generate_sequence_number, get_utc_schedule
from superdesk.publish.formatters import Formatter, get_formatter

from apps.content_types import apply_schema

from ..utils import ContentApiSubscriber


logger = logging.getLogger(__name__)


class BasePublishExchangeFormatter(PublishExchangeFormatter):
    """
    Handles the formatting and processing of publish requests and responses.

    The class is designed to interact with the publishing pipeline, providing
    functionality to process subscribers, destinations, and formatting of items
    to be published. It enables the generation of tasks for publishing queue
    resources and handles specific requirements such as embedding package items
    or filtering document fields based on profiles.
    """

    name: str = "default"

    async def get_request_tasks(
        self, request: PublishRequest, response: PublishRequestResponse
    ) -> tuple[list[PublishQueueResource], list[str]]:
        """
        Retrieves tasks for publishing an item to subscribers and handles formatting issues.

        This asynchronous method generates a list of tasks required for publishing an item
        to the subscribers specified in the response. It processes formatting-specific issues
        encountered for certain subscribers and logs the details of the exceptions if they
        occur during task generation. Tasks and no-formatters are collected and returned
        from this method.

        :param request: An instance of PublishRequest containing details about
            the item to be published and other request metadata.
        :param response: An instance of PublishRequestResponse that
            contains subscriber details and other response metadata.
        :return: A tuple where the first element is a list of PublishQueueResource representing
            publishing tasks for the subscribers, and the second element is a
            list of strings representing subscribers that have formatting issues.
        """

        item = self.filter_item_fields(request.item)
        tasks: list[PublishQueueResource] = []
        no_formatters: list[str] = []
        task_cache: dict[str, list[PublishQueueResource]] = {}
        for subscriber in response.subscribers:
            try:
                subscriber_tasks, subscriber_no_formatters = await self.get_tasks_for_subscriber(
                    request, item, subscriber, response, task_cache
                )
                tasks.extend(subscriber_tasks)
                no_formatters.extend(subscriber_no_formatters)
            except Exception:
                logger.exception(
                    "Failed to queue item for subscriber",
                    extra=dict(
                        item_id=request.item_id,
                        item_headline=item.get("headline"),
                        subscriber_name=subscriber.name,
                    ),
                )

        return tasks, no_formatters

    async def get_tasks_for_subscriber(
        self,
        request: PublishRequest,
        item: dict,
        subscriber: SubscribersResource,
        response: PublishRequestResponse,
        task_cache: dict[str, list[PublishQueueResource]],
    ):
        """
        Retrieves publishing tasks for the provided subscriber and their destinations.

        This asynchronous function processes a set of subscriber destinations to gather
        the publishing tasks to be performed. Tasks are generated based on the subscriber's
        destination configurations and the supplied item details. Unsupported formats are
        recorded separately.

        :param request: The publishing request containing global context and configuration
        :param item: A dictionary representing the item being published. Contains
            details necessary for formatting and packaging.
        :param subscriber: The subscriber resource containing information about the subscriber
        :param response: A response object that holds contextual data for the publishing request,
        :param task_cache: A cache of previously processed tasks, mapped by task type.
        :return: A tuple consisting of:
            - list[PublishQueueResource]: A list of publish queue resources representing
            the tasks to be performed for the provided subscriber.
            - list[str]: A list of formats for which a formatter was not found.
        """

        no_formatters: list[str] = []
        subscriber_dict = subscriber.to_dict()
        content_api_enabled = subscriber.id in response.content_api_subscribers
        tasks: list[PublishQueueResource] = []

        for destination in self.get_subscriber_destinations(request, subscriber, content_api_enabled):
            destination_config = destination.config or {}
            embed_package_items = item[ITEM_TYPE] == ContentType.COMPOSITE and destination_config.get("packaged", False)
            if embed_package_items:
                await self._embed_package_items(item)

            if item.get(PUBLISHED_IN_PACKAGE) and destination_config.get("packaged", False):
                continue

            formatter = get_formatter(destination.format, item)

            if not formatter:  # if formatter not found then record it
                no_formatters.append(destination.format)
                continue

            formatter.set_destination(destination.to_dict(), subscriber_dict)
            tasks.extend(
                await self.get_tasks_for_destination(
                    request,
                    item,
                    subscriber,
                    response,
                    formatter,
                    embed_package_items,
                    destination,
                    task_cache,
                )
            )

        return tasks, no_formatters

    async def get_tasks_for_destination(
        self,
        request: PublishRequest,
        item: dict,
        subscriber: SubscribersResource,
        response: PublishRequestResponse,
        formatter: Formatter,
        embed_package_items: bool,
        destination: SubscriberDestination,
        task_cache: dict[str, list[PublishQueueResource]],
    ) -> list[PublishQueueResource]:
        """
        Generate a list of publish queue resources for a given subscriber destination.

        This asynchronous method handles generating publish queue tasks based on the data provided,
        utilizing caching when possible. It formats the subscriber's data and publishes it, creating
        and returning publish queue resources for further use. The result depends on various factors
        including caching policies, subscriber details, and the destination type.

        :param request: The primary publish request containing item identification and requesting state details.
        :param item: The dictionary containing item details to be formatted and added to the publish queue.
        :param subscriber: Resource object representing the subscriber's details.
        :param response: The publish response object including data like subscriber codes and associations.
        :param formatter: The formatter instance to format the item's details based on required rules.
        :param embed_package_items: Flag indicating whether to embed the package items or not.
        :param destination: The final destination configurations for publishing.
        :param task_cache: A dictionary-structured cache for tasks, indexed by cache id.
        :return: A list of publish queue resources representing the generated tasks for processing.
        :raises RuntimeError: Raised if the formatter returns an unexpected response.
        """

        cache_id = PublishCache.generate_cache_id(
            "format-item", formatter.name or formatter.__class__.__name__, request.item_id
        )
        publish_queue_items: list[PublishQueueResource] | None = (
            None if not formatter.use_cache else task_cache.get(cache_id) or None
        )
        subscriber_dict = subscriber.to_dict()
        tasks: list[PublishQueueResource] = []

        publish_queue_service = PublishQueueResource.get_service()

        if publish_queue_items is not None:
            # Item is available in the PublishCache
            for publish_queue_item in deepcopy(publish_queue_items):
                publish_queue_item.id = ObjectId()
                publish_queue_item.state = (
                    PublishQueueState.SUCCESS
                    if destination.delivery_type == "content_api"
                    else PublishQueueState.ROUTING
                )
                publish_queue_item.is_content_api = destination.delivery_type == "content_api"
                publish_queue_item.subscriber_id = subscriber.id
                publish_queue_item.codes = list(response.subscriber_codes.get(subscriber.id) or set())
                publish_queue_item.destination = destination
                publish_queue_item.published_seq_num = await generate_sequence_number(subscriber)
                publish_queue_item.priority = subscriber.priority
                tasks.append(publish_queue_item)

                await publish_queue_service.create([publish_queue_item])

            return tasks
        else:
            # Either caching is not available for this formatter, or it's the first time that we format
            # this document.
            # publish_queue_items = []
            formatted_items = formatter.format(
                self.filter_item_fields(item) if embed_package_items else item.copy(),
                subscriber_dict,
                list(response.subscriber_codes.get(subscriber.id) or set()),
            )
            if isawaitable(formatted_items):
                formatted_items = await formatted_items

            for publish_data in formatted_items:
                if isinstance(publish_data, tuple):
                    pub_seq_num, formatted_doc = publish_data
                    encoded_item = None
                elif isinstance(publish_data, dict):
                    try:
                        pub_seq_num = publish_data["published_seq_num"]
                        formatted_doc = publish_data["formatted_item"]
                        encoded_item = publish_data.get("encoded_item")
                    except KeyError:
                        raise RuntimeError("Invalid response from formatter")
                else:
                    raise RuntimeError("Invalid response from formatter")

                publish_queue_item = PublishQueueResource(
                    id=ObjectId(),
                    state=PublishQueueState.SUCCESS
                    if destination.delivery_type == "content_api"
                    else PublishQueueState.ROUTING,
                    is_content_api=destination.delivery_type == "content_api",
                    item_id=request.item_id,
                    publishing_action=request.published_state,
                    item_version=item[VERSION],
                    formatted_item=formatted_doc,
                    published_in_package=item.get(PUBLISHED_IN_PACKAGE, None),
                    publish_schedule=get_utc_schedule(item, PUBLISH_SCHEDULE) or None,
                    unique_name=item.get("unique_name", None),
                    content_type=item[ITEM_TYPE],
                    headline=item.get("headline") or item.get("name") or item.get("slugline") or "",
                    ingest_provider=ObjectId(item["ingest_provider"]) if item.get("ingest_provider") else None,
                    associated_items=response.associations.get(subscriber.id, []),
                    # The following fields are required by the model, and will be updated per subscriber & destination
                    published_seq_num=pub_seq_num,
                    subscriber_id=subscriber.id,  # Required by model, updated on push to queue
                    priority=subscriber.priority,
                    codes=list(response.subscriber_codes.get(subscriber.id) or set()),
                    destination=destination,
                    item=item if destination.delivery_type == "content_api" else None,
                )

                if encoded_item:
                    app = get_current_app()
                    binary = BytesIO(encoded_item)
                    publish_queue_item.encoded_item_id = app.storage.put(binary)

                tasks.append(publish_queue_item)
                await publish_queue_service.create([publish_queue_item])

            task_cache[cache_id] = tasks

        return tasks

    def filter_item_fields(self, item: dict) -> dict:
        """
        Filter fields of an item dictionary based on its profile and remove unwanted
        nested data.

        The method takes in an item dictionary, determines its profile using an
        external cache, and applies a schema to it. It also removes any rendition
        entries that have a value of `None` from the nested associations within
        the dictionary. This ensures the item conforms to its expected structure
        based on the given profile.

        :param item: The item dictionary to be filtered and updated.
        :return: The filtered and updated item dictionary.
        """

        # remove fields that should not be there given it's profile.
        cache = PublishCache.get()
        try:
            profile = cache.content_types[str(item["profile"])]
        except (KeyError, TypeError, ValueError):
            profile = None

        item = apply_schema(item, profile)

        # remove `None` valued renditions.
        for association_key in item.get(ASSOCIATIONS, {}):
            association = item[ASSOCIATIONS][association_key]
            if not association:
                continue

            renditions = association.get("renditions", {})
            for null_rendition_key in [k for k in renditions if not renditions[k]]:
                del item[ASSOCIATIONS][association_key]["renditions"][null_rendition_key]

        return item

    def get_subscriber_destinations(
        self, request: PublishRequest, subscriber: SubscribersResource, content_api_enabled: bool
    ) -> list[SubscriberDestination]:
        """
        Extracts and aggregates the destinations for a specific subscriber based on the given parameters.

        This method combines the subscriber's current list of destinations and appends an additional
        destination if content API publishing is enabled and allowed by the parameters. It respects
        optional attributes and handles cases where attributes may be absent safely.

        :param request: The request object containing publishing preferences.
        :param subscriber: The resource representing the subscriber with associated destinations.
        :param content_api_enabled: A flag indicating whether publishing to content API is active.
        :return: A list of destination objects, which includes the subscriber's current
            destinations and, optionally, the content API destination.
        """

        destinations = (subscriber.destinations or []).copy()
        if request.publish_to_content_api and content_api_enabled:
            # Ignore type here, as we know ``ContentApiSubscriber`` has a destination
            destinations.append(ContentApiSubscriber.destinations[0])  # type: ignore[index]

        return destinations

    async def _embed_package_items(self, package: dict) -> None:
        """
        Embeds package items into a given package dictionary.

        This method processes the provided package dictionary and attempts to embed
        relevant package item information by looking up published items. It skips the
        root group and only processes groups containing references. If a required
        resource is not found, it raises an appropriate exception. This function is
        designed for embedding package-level item details into the group reference
        structures of a package for further use.

        :param package: The package dictionary to process and embed package items into.
            It is expected to have a specific structure containing groups and references.
        :raises SuperdeskPublishError: When a referenced package item cannot be found among published resources.
        """

        for group in package.get(GROUPS, []):
            if group[GROUP_ID] == ROOT_GROUP:
                continue
            for ref in group[REFS]:
                if RESIDREF not in ref:
                    continue

                package_item = await get_resource_service("published").find_one_async(
                    req=None, item_id=ref[RESIDREF], _current_version=ref[VERSION]
                )
                if not package_item:
                    msg = gettext("Can not find package {package} published item {item}").format(
                        package=package["item_id"], item=ref["residRef"]
                    )
                    raise await SuperdeskPublishError(500, msg).send_notifications()
                package_item[ID_FIELD] = package_item["item_id"]
                ref["package_item"] = package_item

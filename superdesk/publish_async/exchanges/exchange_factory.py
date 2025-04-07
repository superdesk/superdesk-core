import logging

from bson import ObjectId
from quart_babel import gettext
from eve.utils import ParsedRequest

from superdesk import get_resource_service
from superdesk.core import get_config
from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.utils import SingletonInstance, date_to_str
from superdesk.types import (
    PublishQueueResource,
    PublishQueueState,
    SubscribersResource,
    PublishConsumer,
    PublishRequest,
    PublishRequestResponse,
    PublishExchange,
    PublishExchangeFactory,
    PublishExchangeFilter,
    PublishExchangeFormatter,
    PublishExchangeRouter,
    PublishComponentType,
    PublishSenderType,
    ContentState,
    PublishState,
)
from superdesk.utc import utcnow
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock, is_locked
from superdesk.profiling import ProfileManager
from superdesk.celery_app import celery
from superdesk.errors import SuperdeskApiError

from superdesk.publish_async import get_exchange_factory
from superdesk.resource_fields import ITEM_TYPE, ITEM_STATE

from superdesk.metadata.item import PUBLISH_SCHEDULE, SCHEDULE_SETTINGS

from apps.archive.common import ITEM_OPERATION
from apps.publish.published_item import QUEUE_STATE, PUBLISHED

from ..utils import get_high_priority_celery_queue, get_publish_channel_config, ContentApiSubscriber
from ..consumers import AsyncioPublishConsumer, CeleryPublishConsumer, ContentApiPublishConsumer


logger = logging.getLogger(__name__)


class DefaultPublishExchangeFactory(PublishExchangeFactory, SingletonInstance):
    """
    Factory class for creating various types of consumers and managing tasks.

    This class provides factory methods to create consumer instances based on
    different configurations, as well as methods to handle asynchronous tasks.
    It supports determining consumer types dynamically based on input parameters
    and ensures efficient processing of article transmission tasks with proper
    locking and retry logic.

    .. note::
        This class is not intended to be instantiated directly, instead use the ``get_exchange_factory`` method
        which uses the ``PUBLISH_EXCHANGE_FACTORY`` system config.
    """

    _filter_classes: dict[str, type[PublishExchangeFilter]] = {}
    _formatter_classes: dict[str, type[PublishExchangeFormatter]] = {}
    _router_classes: dict[str, type[PublishExchangeRouter]] = {}
    _exchange_classes: dict[str, type[PublishExchange]] = {}
    _consumer_classes: dict[str, type[PublishConsumer]] = {}

    def _register_filter(self, filter_class: type[PublishExchangeFilter]) -> None:
        """
        Registers a filter component class in the system. Each component is identified by a unique name.

        :param filter_class: The filter component class to be registered. It must have a unique name attribute.
        :raises RuntimeError: If a filter component with the same name is already registered.
        """

        if filter_class.name in self._filter_classes:
            existing_class = self._filter_classes[filter_class.name]
            logger.warning(f"PublishFilter '{filter_class.name}' already registered with '{existing_class}'")
            return

        self._filter_classes[filter_class.name] = filter_class

    def _register_formatter(self, formatter_class: type[PublishExchangeFormatter]) -> None:
        """
        Registers a formatter component class in the system. Each component is identified by a unique name.

        :param formatter_class: The formatter component class to be registered. It must have a unique name attribute.
        :raises RuntimeError: If a filter component with the same name is already registered.
        """

        if formatter_class.name in self._formatter_classes:
            existing_class = self._formatter_classes[formatter_class.name]
            logger.warning(f"PublishFormatter '{formatter_class.name}' already registered with '{existing_class}'")
            return

        self._formatter_classes[formatter_class.name] = formatter_class

    def _register_router(self, router_class: type[PublishExchangeRouter]) -> None:
        """
        Registers a router component class in the system. Each component is identified by a unique name.

        :param router_class: The router component class to be registered. It must have a unique name attribute.
        :raises RuntimeError: If a router component with the same name is already registered.
        """

        if router_class.name in self._router_classes:
            existing_class = self._router_classes[router_class.name]
            logger.warning(f"PublishRouter '{router_class.name}' already registered with '{existing_class}'")
            return

        self._router_classes[router_class.name] = router_class

    def _register_exchange(self, exchange_class: type[PublishExchange]) -> None:
        """
        Registers an exchange component class in the system. Each component is identified by a unique name.

        :param exchange_class: The exchange component class to be registered. It must have a unique name attribute.
        :raises RuntimeError: If an exchange component with the same name is already registered.
        """

        if exchange_class.name in self._exchange_classes:
            existing_class = self._exchange_classes[exchange_class.name]
            logger.warning(f"PublishExchange '{exchange_class.name}' already registered with '{existing_class}'")
            return

        self._exchange_classes[exchange_class.name] = exchange_class

    def _register_consumer(self, consumer_class: type[PublishConsumer]) -> None:
        """
        Registers a consumer component class in the system. Each component is identified by a unique name.

        :param consumer_class: The consumer component class to be registered. It must have a unique name attribute.
        :raises RuntimeError: If a consumer component with the same name is already registered.
        """

        if consumer_class.name in self._consumer_classes:
            existing_class = self._consumer_classes[consumer_class.name]
            logger.warning(f"PublishConsumer '{consumer_class.name}' already registered with '{existing_class}'")
            return

        self._consumer_classes[consumer_class.name] = consumer_class

    def register_component(self, component_class: type[PublishComponentType]) -> None:
        """
        Registers a component class within the appropriate category for further usage.
        This method determines the type of the component class and routes it to the
        specific registration method. If the component does not fit into predefined
        categories, a warning is logged indicating an invalid type.

        Types supported:

        * PublishExchangeFilter
        * PublishExchangeFormatter
        * PublishExchangeRouter
        * PublishExchange
        * PublishConsumer

        Will log a warning if a component type is not currently supported.

        :param component_class: The component class to be registered.
        """

        if issubclass(component_class, PublishExchangeFilter):
            self._register_filter(component_class)
        elif issubclass(component_class, PublishExchangeFormatter):
            self._register_formatter(component_class)
        elif issubclass(component_class, PublishExchangeRouter):
            self._register_router(component_class)
        elif issubclass(component_class, PublishExchange):
            self._register_exchange(component_class)
        elif issubclass(component_class, PublishConsumer):
            self._register_consumer(component_class)
        else:
            logger.warning(f"Unable to register component, invalid type: {component_class}")

    def on_app_shutdown(self, app: SuperdeskAsyncApp) -> None:
        """
        Handles actions to be performed on application shutdown, resetting internal
        states and resources specific to filter, formatter, router, exchange, and
        consumer classes.

        :param app: The app instance to perform shutdown actions on.
        """

        self._filter_classes = {}
        self._formatter_classes = {}
        self._router_classes = {}
        self._exchange_classes = {}
        self._consumer_classes = {}

    def get_exchange(self, request: PublishRequest) -> PublishExchange:
        """
        Gets the exchange object configured to process publishing requests.

        This method uses the item, item type, operation, and sender type from the
        provided PublishRequest object to retrieve the appropriate configuration
        for publishing. The configuration determines which filter, formatter,
        router, and exchange classes to use. These classes are instantiated and
        used to construct an exchange object that manages publishing operations.

        :param request: The PublishRequest object containing details about the item to be published.
        :return: The exchange object configured with the appropriate
            filter, formatter, router, and polling settings, ready to manage
            the publishing operation.
        """

        config = get_publish_channel_config(
            request.item, request.item_type, request.operation, request.sender_type.value
        )

        filter_class = self._filter_classes[config["filter"]]
        formatter_class = self._formatter_classes[config["formatter"]]
        router_class = self._router_classes[config["router"]]
        exchange_class = self._exchange_classes[config["exchange"]]

        return exchange_class(filter_class(), formatter_class(), router_class(), config["polling"])

    def get_consumer(self, name: str) -> PublishConsumer:
        """
        Gets an instance of a consumer object based on the provided consumer name. The returned
        consumer instance allows for operations related to message consumption for the specific
        consumer type associated with the given name.

        :param name: The name of the consumer class to retrieve. This should be an existing key in
            the `_consumer_classes` dictionary.
        :return: An instance of the PublishConsumer class corresponding to the provided name.
        :raises KeyError: If the provided name does not exist in the `_consumer_classes` dictionary.
        """

        return self._consumer_classes[name]()

    async def send(self, request: PublishRequest) -> PublishRequestResponse:
        """
        Sends a publish request to an exchange and handles potential errors.

        This asynchronous method sends a request to publish an item using an exchange
        retrieved based on the request's attributes. It logs the operation and
        handles different types of errors that may occur during the publishing process,
        raising appropriate exceptions with detailed messages.

        :param request: The publish request object containing data required
            for publishing, including the ID of the item to be published.
        :return: A PublishRequestResponse instance from the exchange after processing the publish request.
        :raises SuperdeskApiError: either a required key is missing in the request, or an internal
            server error occurs during publishing.
        """

        try:
            exchange = self.get_exchange(request)
            logger.info(f"Sending request for {request.item_id} to {exchange}")
            return await exchange.send(request)
        except KeyError as e:
            logger.exception("Missing key in request")
            raise SuperdeskApiError.badRequestError(
                message=gettext(f"Key is missing on article to be published: {e}"),
            ) from e
        except Exception as e:
            logger.exception("Something bad happened while publishing item", extra=dict(item_id=request.item_id))
            raise SuperdeskApiError.internalError(
                message=gettext(f"Failed to publish the item: {e}"),
                exception=e,
            ) from e

    def get_subscriber_consumer(self, subscriber: SubscribersResource) -> PublishConsumer:
        """
        Create and return a specific type of consumer based on the subscriber's configuration.

        This class method determines whether to create an asynchronous or a celery-based
        publish consumer depending on whether the subscriber supports asynchronous operations.

        :param subscriber: A subscriber resource containing configuration
            details, including whether asynchronous operations are allowed.
        :return: An instance of PublishConsumer, either asynchronous or celery-based.
        """

        consumer_name: str
        if subscriber.id == ContentApiSubscriber.id:
            consumer_name = ContentApiPublishConsumer.name
        elif subscriber.is_async:
            consumer_name = AsyncioPublishConsumer.name
        else:
            consumer_name = CeleryPublishConsumer.name

        return self.get_consumer(consumer_name)

    async def process_pending_tasks(self) -> None:
        """
        An asynchronous class method to process pending tasks for transmitting articles.
        This method takes care of handling locks, task prioritization, and retry logic to ensure
        tasks are executed in the correct order while avoiding duplicate executions. It uses
        Celery to queue tasks for asynchronous processing efficiently.

        :raises Exception: If any exception occurs during the process, it is logged for debugging purposes.
        """

        with ProfileManager("publish:transmit"):
            lock_name = get_lock_id("Transmit", "Articles")
            if not lock(lock_name, expire=1810):
                logger.info(f"Task: {lock_name} is already running.")
                return

            try:
                for priority in [True, False]:  # top priority first
                    for retries in [False, True]:  # first publish pending, retries after
                        subscriber_ids = await self.get_task_subscriber_ids(retries, priority)
                        for subscriber_id in subscriber_ids:
                            sub_lock_name = get_lock_id("Subscriber", "Transmit", str(subscriber_id))
                            if is_locked(sub_lock_name):
                                logger.info(f"Task: {sub_lock_name} is already running.")
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

    async def send_scheduled_or_pending_content(self) -> None:
        """
        Send scheduled or pending content for publishing.

        This asynchronous function acquires a lock to ensure that the task does not
        run concurrently. It retrieves scheduled content items, checks if there are items to
        process, and enqueues them for processing. The lock is released regardless of
        whether an exception occurs.
        """

        lock_name = get_lock_id("publish", "enqueue_published")
        if not lock(lock_name, expire=310):
            logger.info(f"Enqueue Task: {lock_name} is already running.")
            return

        try:
            items = await self.get_pending_or_scheduled_content_for_publishing()
            if len(items) > 0:
                await self.send_items(items)
        finally:
            unlock(lock_name)

    async def send_items(self, items: list[dict]) -> None:
        """
        Asynchronously sends multiple items to the respective PublishExchange(s).

        This method processes a list of items designated for publishing by
        sending a publish request for each item to a PublishExchange. If an error occurs while
        processing an item, the item is added to a dictionary of failed
        items, along with its respective error.

        :param items: A list of dictionaries representing the items to be published.
        :raises Exception: If any unexpected issue occurs in the `send` method, it will catch
            and log the exception, along with the item causing the failure.
        """

        failed_items = {}

        for queue_item in items:
            try:
                await self.send(
                    PublishRequest(
                        item=queue_item,
                        item_id=queue_item["item_id"],
                        item_type=queue_item[ITEM_TYPE],
                        operation=queue_item[ITEM_OPERATION],
                        published_state=queue_item[ITEM_STATE],
                        sender_type=PublishSenderType.INTERNAL,
                        publish_to_content_api=True,
                    )
                )
            except Exception as error:
                logger.exception(error)
                failed_items[str(queue_item.get("_id"))] = queue_item

        if len(failed_items) > 0:
            logger.error("Failed to publish items", extra=dict(failed_items=failed_items.keys()))

    async def get_pending_or_scheduled_content_for_publishing(self) -> list[dict]:
        """
        Retrieves a list of scheduled items ready for publishing based on specific
        criteria. This function queries the MongoDB collection for items that are in
        the pending queue state, and either not yet scheduled or scheduled with a
        publish schedule that is less than or equal to the current UTC time.

        :return: A list of dictionaries representing the scheduled items that meet the querying criteria.
        """

        query = {
            QUEUE_STATE: PublishState.PENDING,
            "$or": [
                {ITEM_STATE: {"$ne": ContentState.SCHEDULED.value}},
                {
                    ITEM_STATE: ContentState.SCHEDULED.value,
                    f"{SCHEDULE_SETTINGS}.utc_{PUBLISH_SCHEDULE}": {"$lte": date_to_str(utcnow())},
                },
            ],
        }
        request = ParsedRequest()
        request.sort = "publish_sequence_no"
        request.max_results = 200
        return list(get_resource_service(PUBLISHED).get_from_mongo(req=request, lookup=query))

    def _get_queue_lookup(self, retries: bool = False, priority: bool | None = None) -> dict:
        """
        Constructs a query to filter the publish queue based on retries and priority
        parameters.

        The function generates a MongoDB query for fetching records from a publish
        queue based on their state, retry attempt time, and priority. It is designed
        to distinguish between pending and retrying states, optionally filtering by
        priority.

        :param retries: Indicates whether to filter for retrying states.
        :param priority: Optionally filters queue items by priority.
            If None, it matches records where the priority attribute is not set
            or is equal to True.
        :return: A dictionary representing the MongoDB query with conditional predicates based on the provided arguments.
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

    async def get_task_subscriber_ids(self, retries: bool = False, priority: bool | None = None) -> list[ObjectId]:
        """
        Retrieve the subscriber IDs of tasks based on the queue lookup criteria.

        This function asynchronously retrieves a list of `subscriber_id` values by
        performing a distinct query on the `PublishQueueResource` service. The query
        parameters are determined by the specified retry and priority conditions.

        :param retries: Indicates whether the query should include tasks flagged for retry.
        :param priority: Specifies the priority level to filter by. If None, priority filtering is not applied.
        :return: A list of unique subscriber IDs matching the specified query conditions.
        """

        lookup = self._get_queue_lookup(retries, priority)
        return await PublishQueueResource.get_service().mongo_async.distinct("subscriber_id", lookup)

    async def get_subscriber_tasks(
        self, subscriber_id: ObjectId, retries: bool = False, priority: bool | None = None
    ) -> list[PublishQueueResource]:
        """
        Asynchronous function to retrieve subscriber tasks based on the provided lookup filters such as subscriber
        ID, retry status, and priority. This function interacts with the PublishQueueResource service instance
        to query the matching tasks and returns them in a list format. The query results are limited by the
        configured maximum transmit query limit and ordered by creation time and published sequence number.

        :param subscriber_id: The unique identifier of the subscriber whose tasks are to be retrieved.
        :param retries: A flag to indicate whether to include tasks eligible for retries.
        :param priority: If specified, filters the tasks based on priority.
        :return: A list of PublishQueueResource objects matching the applied filters.
        """

        lookup = self._get_queue_lookup(retries, priority)
        lookup["$and"].append({"subscriber_id": subscriber_id})
        return await (
            await PublishQueueResource.get_service().find(
                lookup,
                max_results=get_config(int, "MAX_TRANSMIT_QUERY_LIMIT"),  # limit per subscriber now,
                sort=[("_created", 1), ("published_seq_num", 1)],
            )
        ).to_list()


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

    :param subscriber_id: The unique identifier of the subscriber.
    :param retries: A flag indicating whether previously failed tasks should be retried.
    :param priority: An optional parameter that specifies whether tasks of a certain
        priority should be processed.
    :raises celery.exceptions.SoftTimeLimitExceeded: If the task execution exceeds 600 seconds
    """

    subscriber = await SubscribersResource.get_service().find_by_id(subscriber_id)
    if subscriber is None:
        logger.exception("Subscriber to transmit to not found.", extra=dict(subscriber_id=subscriber_id))
        return

    exchange_factory = get_exchange_factory()
    tasks = await exchange_factory.get_subscriber_tasks(subscriber_id, retries, priority)
    if len(tasks) == 0:
        logger.info(f"No tasks found for subscriber {subscriber_id}")
        return

    await exchange_factory.get_subscriber_consumer(subscriber).process_tasks(subscriber, tasks)

from typing import TypedDict
from dataclasses import field
from enum import Enum, unique

from bson import ObjectId

from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.resources import Dataclass
from superdesk.default_settings import ExchangeConfig

from .subscribers import SubscribersResource, SubscriberType
from .publish_queue import PublishQueueResource
from .products import ProductsResource


@unique
class PublishSenderType(str, Enum):
    """
    Enumeration of types of PublishSender.

    This class defines various types of PublishSender sources, represented
    as string constants. These sources specify how content or messages
    are published using different methods or rules. It is particularly
    useful for applications that differentiate behavior or processing
    based on the origin of publication.
    """

    #: Indicates the PublishRequest came from the Web API
    API = "api"

    #: Indicates the PublishRequest came from an Ingest Routing Rule
    INGEST_RULE = "ingest_rule"

    #: Indicates the PublishRequest came from a Macro
    MACRO = "macro"

    #: Indicates the PublishRequest came from internal code (possibly as a side effect of a user action)
    INTERNAL = "internal"


class PublishRequest(Dataclass):
    """
    Represents a request to publish an item within the system.

    This class encapsulates all necessary information required to execute an
    item publishing operation. It specifies details such as the item to be
    published, its unique identifier, the publishing operation requested, and
    the desired state of the item post-publication. Additionally, it includes
    metadata about the item's type, an optional target media type for
    subscribers, and information on the source of the request. Other optional
    settings include the ability to specify whether the item should be
    published to the Content API and to target specific subscribers for
    publishing actions.
    """

    #: The item to be published
    item: dict

    #: The ID of the item
    item_id: str

    #: The publish operation requested
    operation: str

    #: That intended state of the item after published
    published_state: str

    #: The type of the item
    item_type: str

    #: Optional SubscriberType to target
    target_media_type: SubscriberType | None = None

    #: Where this request is coming from
    sender_type: PublishSenderType = PublishSenderType.INTERNAL

    #: If ``True``, will attempt to publish to the Content API
    publish_to_content_api: bool = False

    # Used by the PublishAction to specifically send to these subscribers only
    subscribers: list[SubscribersResource] | None = None


class PublishRequestResponse(Dataclass):
    """
    Represents the response of a PublishRequest within a PublishExchange.

    This class is used to encapsulate the results of handling a request in a
    PublishExchange, detailing various aspects of the processing outcome. It
    includes references to matched subscribers, products, associations, and
    content API results, providing a comprehensive summary of the operation.
    """

    #: If ``True``, the PublishExchange handled the request successfully
    routed: bool = False

    #: List of Subscribers that matched this item
    subscribers: list[SubscribersResource] = field(default_factory=list)

    #: List of Subscriber IDs that matched the Content API products
    content_api_subscribers: set[ObjectId] = field(default_factory=set)

    #: Map of Subscriber ID to item codes
    subscriber_codes: dict[ObjectId, set[str]] = field(default_factory=dict)

    #: Map of Subscriber ID to Associated Item ID
    associations: dict[ObjectId | str, list[str]] = field(default_factory=dict)

    #: Map of ProductID to Product Codes that matched the request
    product_codes: dict[ObjectId, set[str]] = field(default_factory=dict)

    #: List of Products that matched the request
    matched_products: list[ProductsResource] = field(default_factory=list)

    #: Lif of Content API products that matched the request
    matched_api_products: list[ProductsResource] = field(default_factory=list)


class PublishConsumer:
    """
    Defines the protocol for a publish-consumer that facilitates handling and processing
    tasks and transmitting items between publishers and subscribers.

    This protocol is intended to formalize the behavior of implementing classes that manage
    communication and task dispatch between a publisher's task queue and subscriber resources.
    """

    name: str

    async def process_tasks(self, subscriber: SubscribersResource, tasks: list[PublishQueueResource]) -> None:
        """
        Processes a list of tasks for the provided subscriber resource.

        This asynchronous function is designed to iterate over a list of tasks and
        perform related processing for a given subscriber. The specific implementation
        details must be defined in a subclass or by overriding this method.

        :param subscriber: The subscriber resource that is associated with the task processing.
        :param tasks: A list of publish queue resources representing the tasks to be processed.
        """

        raise NotImplementedError()

    async def transmit_item(self, task: PublishQueueResource) -> bool:
        """
        Transmit a single item asynchronously into the desired publishing queue. This
        method is intended to handle the transmission of a resource item encapsulated
        within a PublishQueueResource object. It is expected to be implemented by
        subclasses or concrete implementations to encapsulate the exact logic for
        transmission.

        :param task: A single resource item that should be published to the queue. This object
            encapsulates all necessary publishing details.
        :return: A boolean value indicating success or failure of the transmission process.
        """
        raise NotImplementedError()


class PublishExchangeFilter:
    name: str

    async def filter_subscribers(self, request: PublishRequest, response: PublishRequestResponse) -> None:
        raise NotImplementedError()


class PublishExchangeFormatter:
    name: str

    async def get_request_tasks(
        self, request: PublishRequest, response: PublishRequestResponse
    ) -> tuple[list[PublishQueueResource], list[str]]:
        raise NotImplementedError()


class PublishExchangeRouter:
    name: str

    async def route_tasks_to_consumers(
        self, request: PublishRequest, response: PublishRequestResponse, tasks: list[PublishQueueResource]
    ) -> None:
        raise NotImplementedError()


class PublishExchange:
    name: str
    polling: bool
    _filter: PublishExchangeFilter
    _formatter: PublishExchangeFormatter
    _router: PublishExchangeRouter

    def __init__(
        self,
        filter_instance: PublishExchangeFilter,
        formatter_instance: PublishExchangeFormatter,
        router_instance: PublishExchangeRouter,
        polling: bool = True,
    ):
        self._filter = filter_instance
        self._formatter = formatter_instance
        self._router = router_instance
        self.polling = polling

    def __repr__(self) -> str:
        return (
            f"PublishExchange("
            f"name={self.name}, "
            f"polling={self.polling}, "
            f"filter={self._filter.name}, "
            f"formatter={self._formatter.name}, "
            f"router={self._router.name})"
        )

    def get_exchange_config(self) -> ExchangeConfig:
        return ExchangeConfig(
            exchange=self.name,
            polling=self.polling,
            filter=self._filter.name,
            formatter=self._formatter.name,
            router=self._router.name,
        )

    async def send(self, request: PublishRequest) -> PublishRequestResponse:
        raise NotImplementedError()


PublishComponentType = PublishExchangeFilter | PublishExchangeFormatter | PublishExchangeRouter | PublishExchange


class PublishExchangeFactory:
    """
    Factory class to manage publish exchange, consumers, and task processing.

    This class provides an interface for registering components, retrieving exchange,
    consumers, and handling publish requests. It also supports asynchronous
    processing for pending and scheduled tasks.
    """

    def register_component(self, component_class: type[PublishComponentType]) -> None:
        raise NotImplementedError()

    def on_app_shutdown(self, app: SuperdeskAsyncApp) -> None:
        pass

    def get_exchange(self, request: PublishRequest) -> PublishExchange:
        raise NotImplementedError()

    def get_consumer(self, name: str) -> PublishConsumer:
        raise NotImplementedError()

    async def send(self, request: PublishRequest) -> PublishRequestResponse:
        raise NotImplementedError()

    async def send_scheduled_or_pending_content(self) -> None:
        raise NotImplementedError()

    async def send_items(self, items: list[dict]) -> None:
        raise NotImplementedError()

    def get_subscriber_consumer(self, subscriber: SubscribersResource) -> PublishConsumer:
        raise NotImplementedError()

    async def process_pending_tasks(self) -> None:
        raise NotImplementedError()

    async def get_subscriber_tasks(
        self, subscriber_id: ObjectId, retries: bool = False, priority: bool | None = None
    ) -> list[PublishQueueResource]:
        raise NotImplementedError()

    async def get_pending_or_scheduled_content_for_publishing(self) -> list[dict]:
        raise NotImplementedError()

    async def get_task_subscriber_ids(self, retries: bool = False, priority: bool | None = None) -> list[ObjectId]:
        raise NotImplementedError()


class ProductItemTestResult(TypedDict):
    product_id: ObjectId
    matched: bool
    name: str
    reason: str

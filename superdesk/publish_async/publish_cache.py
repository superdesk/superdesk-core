from typing import cast, Any
from typing_extensions import Self
from asyncio import gather

from bson import ObjectId
from superdesk.flask import g

from superdesk.types import SubscribersResource, ContentFiltersResource, FilterConditionsResource, ProductsResource
from superdesk import get_resource_service


class PublishCache:
    """Data cache, stored in Flask.g, to be used while processing a publish enqueue request.

    Upon starting of a publish enqueue request, you call ``await PublishCache.init()``,
    this retrieves required data from the DB for future use,
    thereafter you call ``PublishCache.get()`` to retrieve the cache for use.
    """

    #: Dictionary of Subscriber ID active Subscribers
    subscribers: dict[ObjectId, SubscribersResource]

    #: Dictionary of FilterCondition ID to FilterCondition
    filter_conditions: dict[ObjectId, FilterConditionsResource]

    #: Dictionary of ContentFilter ID to ContentFilter
    content_filters: dict[ObjectId, ContentFiltersResource]

    #: Dictionary of ProductID to Product
    products: dict[ObjectId, ProductsResource]

    #: Cache used to store the result of content filtering
    filter_result_cache: dict[str, bool]

    #: Cache for generic use, such as product test results
    cache: dict[str, Any]

    #: List of ContentFilters that have ``is_global == True``
    global_content_filters: list[ContentFiltersResource]

    #: Dictionary of global ContentFilter ID and if it matches the item or not
    global_filter_matches: dict[ObjectId, bool]

    #: Dictionary of ContentProfile ID to ContentProfile (aka ContentType)
    content_types: dict[str, dict] = {}

    async def _init(self) -> None:
        gather_response = await gather(
            SubscribersResource.get_service().get_all_map({"is_active": True}),
            FilterConditionsResource.get_service().get_all_map(),
            ContentFiltersResource.get_service().get_all_map(),
            ProductsResource.get_service().get_all_map(),
        )
        self.subscribers = cast(dict[ObjectId, SubscribersResource], gather_response[0])
        self.filter_conditions = cast(dict[ObjectId, FilterConditionsResource], gather_response[1])
        self.content_filters = cast(dict[ObjectId, ContentFiltersResource], gather_response[2])
        self.products = cast(dict[ObjectId, ProductsResource], gather_response[3])

        # TODO-ASYNC-PUBLISH: Convert this to the async service when available (after rebasing from async branch)
        self.content_types = {
            str(content_type["_id"]): content_type for content_type in get_resource_service("content_types").get_all()
        }

        self.global_content_filters = [
            global_filter for global_filter in self.content_filters.values() if global_filter.is_global
        ]

        self.filter_result_cache = {}
        self.cache = {}
        self.global_filter_matches = {}

    @classmethod
    async def init(cls, force: bool = False) -> Self:
        """
        Initialize the PublishCache handler asynchronously as a class method.

        This method ensures the PublishCache instance is present in the global
        context. If not present or if the `force` parameter is set to True, it
        creates and initializes a new instance, then associates it with the
        global context.

        :param force: Indicates whether to force initialization of the PublishCache even
            if it already exists in the global context.
        :return: The PublishCache instance retrieved or initialized as part of the operation.
        """
        if "publish_cache" not in g or force:
            instance = PublishCache()
            await instance._init()
            setattr(g, "publish_cache", instance)

        return cast(Self, getattr(g, "publish_cache"))

    @classmethod
    def get(cls) -> Self:
        """
        Get the current instance of the PublishCache associated with the context.

        This method retrieves the cached instance of PublishCache from the
        context-local storage. If the PublishCache has not been initialized in
        the current context, a RuntimeError will be raised.

        :return: The cached PublishCache instance from the current context.
        :raises RuntimeError: If PublishCache has not been initialized for the current context.
        """
        try:
            return cast(Self, getattr(g, "publish_cache"))
        except AttributeError:
            raise RuntimeError("PublishCache must be initted first, `await PublishCache.init()`")

    @classmethod
    def generate_cache_id(cls, prefix: str, context_id: str | ObjectId, item_id: str | ObjectId) -> str:
        """
        Generates a unique cache identifier based on provided inputs.

        This method constructs a cache ID by concatenating the given prefix, context ID,
        and an identifier from the item dictionary. The identifier is derived from the
        "_id" or "guid" key in the item dictionary and is converted to a string. This
        cache ID can then be used as a unique identifier for caching purposes.

        :param prefix: A string that will serve as the prefix of the cache identifier.
        :param context_id: A string representing the context identifier to be included in the cache ID.
        :param item_id: The ID of the item to serve as the suffix of the cache identifier.
        :return: A concatenated string serving as the unique cache identifier, consisting
            of the prefix, context ID, and item identifier.
        """
        return "-".join([str(prefix), str(context_id), str(item_id)])

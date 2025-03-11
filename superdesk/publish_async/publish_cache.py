from typing import cast
from typing_extensions import Self
from asyncio import gather

from bson import ObjectId
from superdesk.flask import g

from superdesk.types import SubscribersResource, ContentFiltersResource, FilterConditionsResource, ProductsResource


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
        self.filter_result_cache = {}

    @classmethod
    async def init(cls, force: bool = False) -> Self:
        """
        Initialize the PublishCache handler asynchronously as a class method.

        This method ensures the PublishCache instance is present in the global
        context. If not present or if the `force` parameter is set to True, it
        creates and initializes a new instance, then associates it with the
        global context.

        Parameters:
        force: bool
            Indicates whether to force initialization of the PublishCache even
            if it already exists in the global context.

        Returns:
        Self
            The PublishCache instance retrieved or initialized as part of the
            operation.
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

        Raises:
            RuntimeError: If PublishCache has not been initialized for the current
            context.

        Returns:
            Self: The cached PublishCache instance from the current context.
        """
        try:
            return cast(Self, getattr(g, "publish_cache"))
        except AttributeError:
            raise RuntimeError("PublishCache must be initted first, `await PublishCache.init()`")

    def generate_cache_id(self, prefix: str, context_id: str, item: dict) -> str:
        """
        Generates a unique cache identifier based on provided inputs.

        This method constructs a cache ID by concatenating the given prefix, context ID,
        and an identifier from the item dictionary. The identifier is derived from the
        "_id" or "guid" key in the item dictionary and is converted to a string. This
        cache ID can then be used as a unique identifier for caching purposes.

        Parameters:
            prefix: str
                A string that will serve as the prefix of the cache identifier.
            context_id: str
                A string representing the context identifier to be included in the
                cache ID.
            item: dict
                A dictionary containing item details. The "_id" key or "guid" key
                within the dictionary will be used to generate the unique identifier.

        Returns:
            str:
                A concatenated string serving as the unique cache identifier, consisting
                of the prefix, context ID, and item identifier.
        """
        return "-".join([prefix, str(context_id), str(item.get("_id") or item.get("guid"))])

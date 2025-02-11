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
        if "publish_cache" not in g or force:
            instance = PublishCache()
            await instance._init()
            setattr(g, "publish_cache", instance)

        return cast(Self, getattr(g, "publish_cache"))

    @classmethod
    def get(cls) -> Self:
        try:
            return cast(Self, getattr(g, "publish_cache"))
        except AttributeError:
            raise RuntimeError("PublishCache must be initted first, `await PublishCache.init()`")

    def generate_cache_id(self, prefix: str, context_id: str, item: dict) -> str:
        """filter-match-<filterid>-<articleid>"""
        return "-".join([prefix, str(context_id), str(item.get("_id") or item.get("guid"))])

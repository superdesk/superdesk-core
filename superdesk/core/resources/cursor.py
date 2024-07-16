# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Generic, TypeVar, Type, Optional, List, Union, Literal
from typing_extensions import TypedDict
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor


#: The data type for projections, either a list of field names, or a dictionary containing
#: the field and enable/disable state
ProjectedFieldArg = Union[List[str], Dict[str, Literal[0]], Dict[str, Literal[1]]]


class SearchArgs(TypedDict, total=False):
    """Dictionary containing Elasticsearch search arguments

    This is for use with the `.find` methods in elastic clients
    """

    #: A JSON string containing an elasticsearch query
    source: str

    #: A query string
    q: str

    #: Default field, for use with the query string
    df: str

    #: Default operator, for use with the query string (defaults to "AND")
    default_operator: str

    #: A JSON string containing bool query filters, to be applied to the elastic query
    filter: str

    #: A list of dictionaries containing bool query filters, to be applied to the elastic query
    filters: List[Dict[str, Any]]

    #: A JSON string containing the field projections to filter out the returned fields
    projections: str


class SearchRequest(BaseModel):
    """Dataclass containing Elasticsearch request arguments"""

    model_config = ConfigDict(extra="allow")

    #: Argument for the search filters
    args: Optional[SearchArgs] = None

    #: Sorting to be used
    sort: Optional[str] = None

    #: Maximum number of documents to be returned
    max_results: int = 25

    #: The page number to be returned
    page: int = 1

    #: A JSON string contianing an Elasticsearch where query
    where: Optional[str] = None

    #: If `True`, will include aggregations with the result
    aggregations: bool = False

    #: If `True`, will include highlights with the result
    highlight: bool = False

    #: The field projections to be applied
    projection: Optional[ProjectedFieldArg] = None


ResourceModelType = TypeVar("ResourceModelType", bound="ResourceModel")


class ResourceCursorAsync(Generic[ResourceModelType]):
    def __init__(self, data_class: Type[ResourceModelType]):
        self.data_class = data_class

    def __aiter__(self):
        return self

    async def __anext__(self) -> ResourceModelType:
        raise NotImplementedError()

    async def count(self):
        raise NotImplementedError()

    def get_model_instance(self, data: Dict[str, Any]):
        """Get a model instance from a dictionary of values

        :param data: Dictionary containing values to get a model instance from
        :rtype: ResourceModelType
        :return: A model instance
        """

        # We can't use ``model_construct`` method to construct instance without validation
        # because nested models are not being converted to model instances
        data.pop("_type", None)
        return self.data_class(**data)


class ElasticsearchResourceCursorAsync(ResourceCursorAsync):
    no_hits = {"hits": {"total": 0, "hits": []}}

    def __init__(self, data_class: Type[ResourceModelType], hits=None):
        """Parse hits into docs."""

        super().__init__(data_class)
        self._index = 0
        self.hits = hits if hits else self.no_hits

    async def __anext__(self) -> ResourceModelType:
        try:
            data = self.hits["hits"]["hits"][self._index]
            source = data["_source"]
            source["_id"] = data["_id"]
            source["_type"] = source.pop("_resource", None)
            self._index += 1
            return self.get_model_instance(source)
        except (IndexError, KeyError, TypeError):
            raise StopAsyncIteration

    async def count(self):
        hits = self.hits.get("hits")
        if hits:
            total = hits.get("total")
            if isinstance(total, int):
                return total
            elif isinstance(total, dict) and total.get("value"):
                return int(total["value"])
        return 0

    def extra(self, response: Dict[str, Any]):
        """Add extra info to response"""
        if "facets" in self.hits:
            response["_facets"] = self.hits["facets"]
        if "aggregations" in self.hits:
            response["_aggregations"] = self.hits["aggregations"]


class MongoResourceCursorAsync(ResourceCursorAsync):
    def __init__(
        self,
        data_class: Type[ResourceModelType],
        collection: AsyncIOMotorCollection,
        cursor: AsyncIOMotorCursor,
        lookup: Dict[str, Any],
    ):
        super().__init__(data_class)
        self.collection = collection
        self.cursor = cursor
        self.lookup = lookup

    async def __anext__(self):
        return self.get_model_instance(await self.cursor.next())

    async def count(self):
        return await self.collection.count_documents(self.lookup)


from .model import ResourceModel  # noqa: E402

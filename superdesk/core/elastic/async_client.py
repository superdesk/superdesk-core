# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Optional, List, Dict, Any, Tuple, cast, overload
import logging

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError, TransportError, RequestError
from elasticsearch.helpers import async_bulk

from superdesk.core.types import SearchRequest
from .base_client import BaseElasticResourceClient, ElasticCursor, InvalidSearchString, ProjectedFieldSources


logger = logging.getLogger(__name__)


class ElasticResourceAsyncClient(BaseElasticResourceClient):
    elastic: AsyncElasticsearch

    async def insert(self, docs: List[Dict[str, Any]]) -> List[str]:
        """Insert a list of documents into Elasticsearch.

        :param docs: List of documents to insert.
        :return: List of IDs for the inserted documents.
        """

        ids: List[str] = []
        for doc, doc_id in self._iter_docs_to_insert(docs):
            await self.elastic.create(**self._get_insert_args(doc, doc_id))
            ids.append(doc_id)

        if self.config.force_refresh:
            await self.elastic.indices.refresh(index=self.config.index)

        return ids

    async def bulk_insert(self, docs: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]]]:
        """Insert a list of documents into Elasticsearch.

        :param docs: List of documents to insert.
        :return: Tuple containing the number of inserted documents and the number of failed inserts
        """

        success, failed = await async_bulk(self.elastic, **self._get_bulk_insert_args(docs))
        if self.config.force_refresh:
            await self.elastic.indices.refresh(index=self.config.index)

        # Cast `failed` to dict, because if we pass `stats_only=False`, then we get the full document
        # where as if `stats_only=True`, then `failed` is just a number
        return success, cast(List[Dict[str, Any]], failed)

    async def update(self, item_id: str, updates: Dict[str, Any]) -> Any:
        """Update a document in Elasticsearch

        :param item_id: ID of the document to update.
        :param updates: Dictionary of updates to be applied.
        :return: The response from Elasticsearch.
        """

        return await self.elastic.update(**self._get_update_args(item_id, updates))

    async def replace(self, item_id: str, updates: Dict[str, Any]) -> Any:
        """Replace an entire document in Elasticsearch

        :param item_id: ID of the document to update.
        :param updates: Document used to replace the item.
        :return: The response from Elasticsearch.
        """

        return await self.elastic.index(**self._get_replace_args(item_id, updates))

    async def remove(self, item_id: str) -> Any:
        """Delete a document from Elasticsearch

        :param item_id: ID of the document to delete.
        :return: The response from Elasticsearch.
        """

        return await self.elastic.delete(**self._get_remove_args(item_id))

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Get the number of documents in Elasticsearch that match the search query

        :param query: The search query to filter items by.
        :return: The number of documents in Elasticsearch that matches the query.
        """

        result = await self.elastic.count(**self._get_count_args(query))
        return result.get("count", 0)

    async def is_empty(self) -> bool:
        """Utility function used to see if an index has no documents

        :return: True if the index is empty, False otherwise
        """

        return (await self.count()) == 0

    async def search(self, query: Dict[str, Any], indexes: Optional[List[str]] = None) -> Any:
        """Perform a raw search against the Elasticsearch index

        :param query: The search query to filter items by.
        :param indexes: An optional list of indexes to search in.
        :return: The response from Elasticsearch.
        """

        return await self.elastic.search(**self._get_search_args(query, indexes))

    async def find_by_id(self, item_id: str, projection: ProjectedFieldSources | None = None) -> dict[str, Any] | None:
        """Find a single document in Elasticsearch based on its ID

        :param item_id: ID of the document to find.
        :return: The document found or None if no document was found.
        """

        try:
            response = await self.elastic.get(index=self.config.index, id=item_id, **(projection or {}))

            if "exists" in response:
                response["found"] = response["exists"]

            if not response.get("found"):
                return None

            docs = self._parse_hits({"hits": {"hits": [response]}})
            return docs.first()

        except NotFoundError:
            return None
        except TransportError as tex:
            if tex.error == "routing_missing_exception" or "RoutingMissingException" in tex.error:
                try:
                    response = await self.elastic.search(
                        index=self.config.index,
                        body={"query": {"bool": {"must": [{"term": {"_id": item_id}}]}}},
                        size=1,
                    )
                    docs = self._parse_hits(response)
                    return docs.first()
                except NotFoundError:
                    return None
        return None

    @overload
    async def find_one(self, req: SearchRequest) -> dict[str, Any] | None:
        ...

    @overload
    async def find_one(self, req: dict) -> dict[str, Any] | None:
        ...

    async def find_one(self, req: SearchRequest | dict) -> Optional[Dict[str, Any]]:
        """Find a single document in Elasticsearch based on the provided search query

        :param lookup: kwargs providing the filters used to search for an item
        :return: The document found or None if no document was found.
        """

        search_request = req if isinstance(req, SearchRequest) else SearchRequest(where=req)

        if isinstance(search_request.where, dict) and set(search_request.where.keys()) == {"_id"}:
            return await self.find_by_id(search_request.where["_id"], self._get_projected_fields(search_request) or {})

        try:
            response = await self.elastic.search(**self._get_find_one_args(search_request))

            docs = self._parse_hits(response)
            return docs.first()
        except NotFoundError:
            return None

    async def find_list_of_ids(self, ids: List[str]) -> ElasticCursor:
        """Find multiple documents in Elasticsearch based on their IDs

        :param ids: The list of IDs used to search for
        :return: An ElasticCursor instance with the search results
        """

        return self._parse_hits(
            await self.elastic.mget(
                index=self.config.index,
                body={"ids": ids},
            )
        )

    async def find(self, req: SearchRequest, sub_resource_lookup: Optional[Dict[str, Any]] = None):
        """Find documents in Elasticsearch

        :param req: A SearchRequest instance with the search params to be used
        :param sub_resource_lookup: Optional additional lookup filters
        :return: A tuple containing an ElasticCursor instance and the number of documents found
        """

        args = self._get_find_args(req, sub_resource_lookup)

        try:
            response = await self.elastic.search(**args)
        except RequestError as e:
            if e.status_code == 400:
                if "No mapping found for" in e.error:
                    response = {}
                elif (
                    "SearchParseException" in e.error
                    or "x_content_parse_exception" in e.error
                    or "parsing_exception" in e.error
                ):
                    query = args.get("body")
                    logger.warning(f"Invalid search string: {query}")
                    raise InvalidSearchString
                else:
                    raise
            else:
                raise

        cursor = self._parse_hits(response)
        return cursor, cursor.count()

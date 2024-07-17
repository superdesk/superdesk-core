# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Optional, List, Dict, Any, Tuple, cast

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, TransportError, RequestError
from elasticsearch.helpers import bulk

from ..resources.cursor import SearchRequest
from .base_client import BaseElasticResourceClient, ElasticCursor, InvalidSearchString


class ElasticResourceClient(BaseElasticResourceClient):
    elastic: Elasticsearch

    def insert(self, docs: List[Dict[str, Any]]) -> List[str]:
        """Insert a list of documents into Elasticsearch.

        :param docs: List of documents to insert.
        :return: List of IDs for the inserted documents.
        """

        ids: List[str] = []
        for doc, doc_id in self._iter_docs_to_insert(docs):
            self.elastic.create(**self._get_insert_args(doc, doc_id))
            ids.append(doc_id)

        if self.config.force_refresh:
            self.elastic.indices.refresh(index=self.config.index)

        return ids

    def bulk_insert(self, docs: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]]]:
        """Insert a list of documents into Elasticsearch.

        :param docs: List of documents to insert.
        :return: Tuple containing the number of inserted documents and the number of failed inserts
        """

        success, failed = bulk(self.elastic, **self._get_bulk_insert_args(docs))
        if self.config.force_refresh:
            self.elastic.indices.refresh(index=self.config.index)

        # Cast `failed` to dict, because if we pass `stats_only=False`, then we get the full document
        # where as if `stats_only=True`, then `failed` is just a number
        return success, cast(List[Dict[str, Any]], failed)

    def update(self, item_id: str, updates: Dict[str, Any]) -> Any:
        """Update a document in Elasticsearch

        :param item_id: ID of the document to update.
        :param updates: Dictionary of updates to be applied.
        :return: The response from Elasticsearch.
        """

        return self.elastic.update(**self._get_update_args(item_id, updates))

    def replace(self, item_id: str, updates: Dict[str, Any]) -> Any:
        """Replace an entire document in Elasticsearch

        :param item_id: ID of the document to update.
        :param updates: Document used to replace the item.
        :return: The response from Elasticsearch.
        """

        return self.elastic.index(**self._get_replace_args(item_id, updates))

    def remove(self, item_id: str) -> Any:
        """Delete a document from Elasticsearch

        :param item_id: ID of the document to delete.
        :return: The response from Elasticsearch.
        """

        return self.elastic.delete(**self._get_remove_args(item_id))

    def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Get the number of documents in Elasticsearch that match the search query

        :param query: The search query to filter items by.
        :return: The number of documents in Elasticsearch that matches the query.
        """

        result = self.elastic.count(**self._get_count_args(query))
        return result.get("count", 0)

    def is_empty(self) -> bool:
        """Utility function used to see if an index has no documents

        :return: True if the index is empty, False otherwise
        """

        return self.count() == 0

    def search(self, query: Dict[str, Any], indexes: Optional[List[str]] = None) -> Any:
        """Perform a raw search against the Elasticsearch index

        :param query: The search query to filter items by
        :param indexes: An optional list of indexes to search in
        :return: The response from Elasticsearch
        """

        return self.elastic.search(**self._get_search_args(query, indexes))

    def find_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Find a single document in Elasticsearch based on its ID

        :param item_id: ID of the document to find.
        :return: The document found or None if no document was found.
        """

        try:
            response = self.elastic.get(index=self.config.index, id=item_id)

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
                    response = self.elastic.search(
                        index=self.config.index,
                        body={"query": {"bool": {"must": [{"term": {"_id": item_id}}]}}},
                        size=1,
                    )
                    docs = self._parse_hits(response)
                    return docs.first()
                except NotFoundError:
                    return None
        return None

    def find_one(self, **lookup) -> Optional[Dict[str, Any]]:
        """Find a single document in Elasticsearch based on the provided search query

        :param lookup: kwargs providing the filters used to search for an item
        :return: The document found or None if no document was found.
        """

        if "_id" in lookup:
            return self.find_by_id(lookup["_id"])

        filters = [{"term": {key: val}} for key, val in lookup.items()]
        query = {"query": {"bool": {"must": filters}}}

        try:
            response = self.elastic.search(index=self.config.index, body=query, size=1)

            docs = self._parse_hits(response)
            return docs.first()
        except NotFoundError:
            return None

    def find_list_of_ids(self, ids: List[str]) -> ElasticCursor:
        """Find multiple documents in Elasticsearch based on their IDs

        :param ids: The list of IDs used to search for
        :return: An ElasticCursor instance with the search results
        """

        return self._parse_hits(
            self.elastic.mget(
                index=self.config.index,
                body={"ids": ids},
            )
        )

    def find(
        self, req: SearchRequest, sub_resource_lookup: Optional[Dict[str, Any]] = None
    ) -> Tuple[ElasticCursor, int]:
        """Find documents in Elasticsearch

        :param req: A SearchRequest instance with the search params to be used
        :param sub_resource_lookup: Optional additional lookup filters
        :return: A tuple containing an ElasticCursor instance and the number of documents found
        """

        try:
            response = self.elastic.search(**self._get_find_args(req, sub_resource_lookup))
        except RequestError as e:
            if e.status_code == 400 and "No mapping found for" in e.error:
                response = {}
            elif e.status_code == 400 and "SearchParseException" in e.error:
                raise InvalidSearchString
            else:
                raise

        cursor = self._parse_hits(response)
        return cursor, cursor.count()

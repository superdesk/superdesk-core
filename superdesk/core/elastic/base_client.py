# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Optional, Iterator, List, Tuple, Union, TypedDict
import ast

import simplejson as json
from eve.io.mongo.parser import parse

from superdesk.errors import SuperdeskApiError
from superdesk.core.types import ProjectedFieldArg, SearchRequest, SortParam
from superdesk.core.resources import get_projection_from_request

from .common import ElasticClientConfig, ElasticResourceConfig


class InvalidSearchString(Exception):
    """Exception thrown when search string has invalid value"""

    pass


class ProjectedFieldSources(TypedDict, total=False):
    _source: Optional[str]
    _source_excludes: Optional[str]


# TODO: Make this Cursor and Mongo cursor implement the same protocol
class ElasticCursor:
    no_hits = {"hits": {"total": 0, "hits": []}}

    def __init__(self, hits=None, docs=None):
        """Parse hits into docs."""
        self.hits = hits if hits else self.no_hits
        self.docs = docs if docs else []

    def __getitem__(self, key):
        return self.docs[key]

    def first(self):
        """Get first doc."""
        return self.docs[0] if self.docs else None

    def count(self, **kwargs):
        """Get hits count."""
        hits = self.hits.get("hits")
        if hits:
            total = hits.get("total")
            if isinstance(total, int):
                return total
            elif total and total.get("value"):
                return int(total["value"])
        return 0

    def extra(self, response):
        """Add extra info to response."""
        if "facets" in self.hits:
            response["_facets"] = self.hits["facets"]
        if "aggregations" in self.hits:
            response["_aggregations"] = self.hits["aggregations"]


class BaseElasticResourceClient:
    resource_name: str
    config: ElasticClientConfig
    resource_config: ElasticResourceConfig

    def __init__(self, resource_name: str, config: ElasticClientConfig, resource_config: ElasticResourceConfig) -> None:
        self.resource_name = resource_name
        self.config = config
        self.resource_config = resource_config

    def _prepare_for_storage(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Union[str, None]]]:
        doc = data.copy()
        doc_id = doc.pop("_id", None)
        doc.pop("_type", None)
        doc["_resource"] = self.resource_name
        return doc, doc_id

    def _iter_docs_to_insert(self, docs: List[Dict[str, Any]]) -> Iterator[Tuple[Dict[str, Any], str]]:
        for doc in docs:
            data, doc_id = self._prepare_for_storage(doc)
            if doc_id is None:
                # Document does not contain an `_id` attribute, can't insert this one
                continue
            yield data, str(doc_id)
        return

    def _get_insert_args(self, doc, item_id) -> Dict[str, Any]:
        return dict(
            body=doc,
            id=item_id,
            index=self.config.index,
        )

    def _get_bulk_insert_args(self, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        actions: List[Dict[str, Any]] = [
            dict(_source=doc, _id=doc_id) for doc, doc_id in self._iter_docs_to_insert(docs)
        ]
        return dict(
            index=self.config.index,
            actions=actions,
            stats_only=False,
        )

    def _get_update_args(self, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        updates_dict, _id = self._prepare_for_storage(updates)
        return dict(
            index=self.config.index,
            id=item_id,
            body=dict(doc=updates_dict),
            refresh=True,
            retry_on_conflict=self.config.retry_on_conflict,
        )

    def _get_replace_args(self, item_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        doc, _id = self._prepare_for_storage(document)

        return dict(
            index=self.config.index,
            id=item_id,
            body=doc,
            refresh=True,
        )

    def _get_remove_args(self, item_id: str) -> Dict[str, Any]:
        return dict(
            index=self.config.index,
            id=item_id,
            refresh=True,
        )

    def _get_count_args(self, query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return dict(index=self.config.index, body=query or {"query": {"match_all": {}}})

    def _get_search_args(self, query: Dict[str, Any], indexes: Optional[List[str]] = None) -> Dict[str, Any]:
        return dict(
            index=indexes if indexes is not None else self.config.index,
            body=query,
            track_total_hits=self.config.track_total_hits,
        )

    def _get_find_args(
        self, req: SearchRequest, sub_resource_lookup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        args = req.args or {}
        if args.get("source"):
            query: Dict[str, Any] = json.loads(args["source"])
            query.setdefault("query", {})
            must = []
            for key, val in query["query"].items():
                if key != "bool":
                    must.append({key: val})
            if must:
                query["query"] = {"bool": {"must": must}}
        else:
            query = {"query": {"bool": {}}}

        if args.get("q"):
            query["query"]["bool"].setdefault("must", []).append(
                _build_query_string(
                    args["q"],
                    default_field=args.get("df"),
                    default_operator=args.get("default_operator", "OR"),
                )
            )

        if "sort" not in query:
            if req.sort:
                _set_sort(query, req.sort)
            elif self.resource_config.default_sort:
                _set_sort(query, self.resource_config.default_sort)

        if not req.max_results and self.resource_config.default_max_results:
            req.max_results = self.resource_config.default_max_results

        if req.max_results:
            query.setdefault("size", req.max_results)

        if req.page > 1 and req.max_results:
            query.setdefault("from", (req.page - 1) * req.max_results)

        filters = []
        if self.resource_config.filter:
            filters.append(self.resource_config.filter)

        if self.resource_config.filter_callback:
            filters.append(self.resource_config.filter_callback(req))

        if sub_resource_lookup:
            filters.append({"bool": {"must": [{"term": {key: val}} for key, val in sub_resource_lookup.items()]}})

        if "filter" in args:
            filters.append(json.loads(args["filter"]))

        if "filters" in args:
            filters.extend(args["filters"])

        if req.where:
            try:
                term = json.loads(req.where) if isinstance(req.where, str) else req.where
                filters.append({"term": term})
            except ValueError:
                try:
                    filters.append({"term": parse(req.where)})
                except ValueError as e:
                    raise SuperdeskApiError.badRequestError("Invalid where argument") from e

        _set_filters(query, filters)

        if self.resource_config.facets:
            query["facets"] = self.resource_config.facets

        if self.resource_config.aggregations and (self.config.auto_aggregations or req.aggregations):
            query["aggs"] = self.resource_config.aggregations

        if self.resource_config.highlight and req.highlight:
            for q in query["query"].get("bool", {}).get("must", []):
                if q.get("query_string"):
                    highlights = self.resource_config.highlight(q["query_string"])

                    if highlights:
                        query["highlight"] = highlights
                        query["highlight"].setdefault("require_field_match", False)

        return dict(
            index=self.config.index,
            track_total_hits=self.config.track_total_hits,
            **(self._get_projected_fields(req) or {}),
            body=query,
        )

    def _get_projected_fields(self, req: SearchRequest) -> ProjectedFieldSources | None:
        projection_include, projection_fields = get_projection_from_request(req)

        if not projection_fields:
            return None
        elif projection_include:
            return ProjectedFieldSources(_source=",".join(projection_fields))
        else:
            return ProjectedFieldSources(_source_excludes=",".join(projection_fields))

    def _parse_hits(self, hits) -> ElasticCursor:
        docs = []
        for hit in hits.get("hits", {}).get("hits", []):
            docs.append(self._format_doc(hit))
        return ElasticCursor(hits, docs)

    def _format_doc(self, hit: Dict[str, Any]):
        doc: Dict[str, Any] = hit.get("_source", {})
        doc.setdefault("_id", hit.get("_id"))
        doc.pop("_resource", None)
        doc["_type"] = self.resource_name
        if hit.get("highlight"):
            doc["es_highlight"] = hit["highlight"]

        if hit.get("inner_hits"):
            doc["_inner_hits"] = {}
            for key, value in hit["innter_hits"].items():
                doc["inner_hits"][key] = []
                for item in value.get("hits", {}).get("hits", []):
                    doc["_inner_hits"][key].append(item)

        return doc


def _set_sort(query: dict, sort: SortParam | None) -> None:
    if sort is None:
        return

    query["sort"] = []
    sort_list = ast.literal_eval(sort) if isinstance(sort, str) else sort
    for key, sortdir in sort_list:
        sort_dict = dict([(key, "asc" if sortdir > 0 else "desc")])
        query["sort"].append(sort_dict)


def _set_filters(query, filters):
    """Put together all filters we have and set them as 'and' filter
    within filtered query.

    :param query: elastic query being constructed
    :param base_filters: all filters set outside of query (eg. resource config, sub_resource_lookup)
    """
    query["query"].setdefault("bool", {})
    if filters:
        for f in filters:
            if f is not None:
                query["query"]["bool"].setdefault("filter", []).append(f)


def _build_query_string(q, default_field=None, default_operator="AND"):
    """
    Build ``query_string`` object from ``q``.

    :param q: q of type String
    :param default_field: default_field
    :return: dictionary object.
    """

    def _is_phrase_search(query_string):
        clean_query = query_string.strip()
        return clean_query and clean_query.startswith('"') and clean_query.endswith('"')

    def _get_phrase(query_string):
        return query_string.strip().strip('"')

    if _is_phrase_search(q) and default_field:
        query = {"match_phrase": {default_field: _get_phrase(q)}}
    else:
        query = {
            "query_string": {
                "query": q,
                "default_operator": default_operator,
                "lenient": True,
            }
        }
        if default_field:
            query["query_string"]["default_field"] = default_field

    return query

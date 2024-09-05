# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from uuid import uuid4

from ..config import ConfigModel
from superdesk.core.types import SearchRequest, SortParam


@dataclass
class ElasticResourceConfig:
    """Resource config for use with Elasticsearch, to be included with the ResourceConfig"""

    #: Config prefix to be used
    prefix: str = "ELASTICSEARCH"

    #: The default sort
    default_sort: SortParam | None = None

    #: The default maximum number of documents to be returned
    default_max_results: Optional[int] = None

    #: An optional filter to be applied to all searches
    filter: Optional[Dict[str, Any]] = None

    #: An optional callback used to construct a filter dynamically, to be applied to all searches
    filter_callback: Optional[Callable[[Optional[SearchRequest]], Dict[str, Any]]] = None

    #: An optional dictionary of field aggregations
    aggregations: Optional[Dict[str, Any]] = None

    #: An optional dictionary of highlights to be applied
    highlight: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None

    #: An optional list of facets to be applied (Will this be required in new version?)
    facets: Optional[Dict[str, Any]] = None


class ElasticClientConfig(ConfigModel):
    """Dataclass for storing an Elastic config for a specific resource"""

    #: The index prefix to use for the resource
    index: str = "superdesk"

    #: The URL of the Elasticsearch instance to connect to
    url: str = "http://localhost:9200"

    #: Refresh the Elasticsearch index after uploading documents to the index
    force_refresh: bool = True

    #: If ``True``, automatically requests aggregations on search.
    auto_aggregations: bool = True

    #: Set the default ``track_total_hits`` for search requests. See https://www.elastic.co/guide/en/elasticsearch/reference/master/search-your-data.html#track-total-hits
    track_total_hits: int = 10000

    #: Number of retries when timing out
    retry_on_timeout: bool = True

    #: Maximum number of retries
    max_retries: int = 3

    #: Number of retries on update if there is a conflict
    retry_on_conflict: int = 5

    #: Optional dict to use when connecting to an Elasticsearch instance
    options: Optional[Dict[str, Any]] = None

    #: Settings to be placed on the Elasticsearch index when creating it
    settings: Optional[Dict[str, Any]] = None


def generate_index_name(alias: str):
    random = str(uuid4()).split("-")[0]
    return "{}_{}".format(alias, random)

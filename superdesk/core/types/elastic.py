from typing import Any, Callable
from dataclasses import dataclass

from ..config import ConfigModel
from .search import SearchRequest, SortParam


@dataclass
class ElasticResourceConfig:
    """Resource config for use with Elasticsearch, to be included with the ResourceConfig"""

    #: Config prefix to be used
    prefix: str = "ELASTICSEARCH"

    #: The default sort
    default_sort: SortParam | None = None

    #: The default maximum number of documents to be returned
    default_max_results: int = 25

    #: An optional filter to be applied to all searches
    filter: dict[str, Any] | None = None

    #: An optional callback used to construct a filter dynamically, to be applied to all searches
    filter_callback: Callable[[SearchRequest | None], dict[str, Any]] | None = None

    #: An optional dictionary of field aggregations
    aggregations: dict[str, Any] | None = None

    #: An optional dictionary of highlights to be applied
    highlight: Callable[[str], dict[str, Any] | None] | None = None

    #: An optional list of facets to be applied (Will this be required in new version?)
    facets: dict[str, Any] | None = None


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
    options: dict[str, Any] | None = None

    #: Settings to be placed on the Elasticsearch index when creating it
    settings: dict[str, Any] | None = None

from typing import Any, Literal
from typing_extensions import TypedDict
from enum import Enum, unique

from pydantic import BaseModel, ConfigDict, NonNegativeInt, field_validator, Field
from pydantic.dataclasses import dataclass


#: The data type for projections, either a list of field names, or a dictionary containing
#: the field and enable/disable state
ProjectedFieldArg = (
    list[str]
    | set[str]
    | dict[str, Literal[0]]
    | dict[str, Literal[1]]
    | dict[str, Literal[True]]
    | dict[str, Literal[False]]
)

#: Type used to provide list of sort params to be used
SortListParam = list[tuple[str, Literal[1, -1]]]

#: Type used for sort param in service requests
#: can be a string, which will convert to an :attr:`SortListParam` type
SortParam = str | SortListParam

#: Type used for version param in service requests
#: Can be either ``"all"`` or an int ``>= 0``
VersionParam = Literal["all"] | NonNegativeInt


class SearchArgs(TypedDict, total=False):
    """Dictionary containing Elasticsearch search arguments

    This is for use with the `.find` methods in elastic clients
    """

    #: A JSON string containing an elasticsearch query
    source: str | dict

    #: A query string
    q: str

    #: Default field, for use with the query string
    df: str

    #: Default operator, for use with the query string (defaults to "AND")
    default_operator: str

    #: A JSON string containing bool query filters, to be applied to the elastic query
    filter: str | dict

    #: A list of dictionaries containing bool query filters, to be applied to the elastic query
    filters: list[dict[str, Any]]

    #: A JSON string containing the field projections to filter out the returned fields
    projections: str

    version: VersionParam | None


@dataclass
class ESBoolQuery:
    must: list[dict[str, Any]] = Field(default_factory=list)
    must_not: list[dict[str, Any]] = Field(default_factory=list)
    should: list[dict[str, Any]] = Field(default_factory=list)
    filter: list[dict[str, Any]] = Field(default_factory=list)
    minimum_should_match: int | None = None
    highlight: dict[str, Any] = Field(default_factory=dict)

    def has_filters(self):
        return (
            len(self.must) > 0
            or len(self.must_not) > 0
            or len(self.should) > 0
            or len(self.filter) > 0
            or len(self.highlight) > 0
        )


@dataclass
class ESQuery:
    query: ESBoolQuery = Field(default_factory=ESBoolQuery)
    post_filter: ESBoolQuery = Field(default_factory=ESBoolQuery)
    aggs: dict[str, Any] = Field(default_factory=dict)
    include_fields: list[str] = Field(default_factory=list)
    exclude_fields: list[str] = Field(default_factory=list)

    def generate_query_dict(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        if query is None:
            query = {}

        if self.query.has_filters():
            query.setdefault("query", {}).setdefault("bool", {})
            if self.query.must:
                query["query"]["bool"].setdefault("must", []).extend(self.query.must)
            if self.query.must_not:
                query["query"]["bool"].setdefault("must_not", []).extend(self.query.must_not)
            if self.query.should:
                query["query"]["bool"].setdefault("should", []).extend(self.query.should)
                minimum_should_match = self.query.minimum_should_match
                query["query"]["bool"]["minimum_should_match"] = (
                    minimum_should_match if minimum_should_match is not None else 1
                )
            if self.query.filter:
                query["query"]["bool"].setdefault("filter", []).extend(self.query.filter)

            if self.query.highlight:
                query["highlight"] = self.query.highlight

        if self.post_filter.has_filters():
            query.setdefault("post_filter", {}).setdefault("bool", {})
            if self.post_filter.must:
                query["post_filter"]["bool"]["must"] = self.post_filter.must
            if self.post_filter.must_not:
                query["post_filter"]["bool"]["must_not"] = self.post_filter.must_not
            if self.post_filter.must_not:
                query["post_filter"]["bool"]["should"] = self.post_filter.should
                minimum_should_match = self.post_filter.minimum_should_match
                query["query"]["bool"]["minimum_should_match"] = (
                    minimum_should_match if minimum_should_match is not None else 1
                )
            if self.post_filter.filter:
                query["post_filter"]["bool"]["filter"] = self.post_filter.filter

        # these two are mutually exclusive
        if self.include_fields:
            query.setdefault("_source", {}).setdefault("includes", []).extend(self.include_fields)
        elif self.exclude_fields:
            query.setdefault("_source", {}).setdefault("excludes", []).extend(self.exclude_fields)

        return query


class SearchRequest(BaseModel):
    """Dataclass containing Elasticsearch request arguments"""

    model_config = ConfigDict(extra="allow")

    #: Argument for the search filters
    args: SearchArgs | None = None

    #: Sorting to be used
    sort: SortParam | None = None

    #: Maximum number of documents to be returned
    # TODO-ASYNC: Support None for `max_results`, and let the underlying resource service handle that instead
    max_results: int = 25

    #: The page number to be returned
    page: int = 1

    #: A JSON string contianing an Elasticsearch where query
    where: str | dict | None = None

    #: If `True`, will include aggregations with the result
    aggregations: bool = False

    #: If `True`, will include highlights with the result
    highlight: bool = False

    #: The field projections to be applied
    projection: ProjectedFieldArg | None = None

    version: int | None = None

    use_mongo: bool | None = None

    elastic: ESQuery = Field(default_factory=ESQuery)

    @field_validator("projection", mode="before")
    def parse_projection(cls, value: ProjectedFieldArg | str | None) -> ProjectedFieldArg | None:
        from superdesk.core import json

        return json.loads(value) if isinstance(value, str) else value

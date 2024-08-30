# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Optional, List, Union, Literal
from typing_extensions import TypedDict

from pydantic import BaseModel, ConfigDict, NonNegativeInt


#: The data type for projections, either a list of field names, or a dictionary containing
#: the field and enable/disable state
ProjectedFieldArg = Union[List[str], Dict[str, Literal[0]], Dict[str, Literal[1]]]
SortListParam = list[tuple[str, Literal[1, -1]]]
SortParam = str | SortListParam
VersionParam = Literal["all"] | NonNegativeInt


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

    version: VersionParam | None


class SearchRequest(BaseModel):
    """Dataclass containing Elasticsearch request arguments"""

    model_config = ConfigDict(extra="allow")

    #: Argument for the search filters
    args: Optional[SearchArgs] = None

    #: Sorting to be used
    sort: SortParam | None = None

    #: Maximum number of documents to be returned
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
    projection: Optional[ProjectedFieldArg] = None

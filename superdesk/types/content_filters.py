from typing import Annotated

from superdesk.core.resources import ResourceModelWithObjectId, Dataclass, fields
from superdesk.core.resources.validators import validate_iunique_value_async, validate_data_relation_async


class ContentFilterExpression(Dataclass):
    fc: Annotated[list[fields.ObjectId] | None, validate_data_relation_async("filter_conditions")] = None
    pf: Annotated[list[fields.ObjectId] | None, validate_data_relation_async("content_filters")] = None


class ContentFilter(Dataclass):
    expression: ContentFilterExpression


class ContentFiltersResource(ResourceModelWithObjectId):
    name: Annotated[str, validate_iunique_value_async("content_filters", "name")]
    content_filter: list[ContentFilter] | None = None
    is_global: bool = False
    is_archived_filter: bool = False
    api_block: bool = False

import enum
from typing import Any, Annotated
from datetime import datetime

from pydantic import Field

from superdesk.core.resources import ResourceModelWithObjectId
from superdesk.core.resources.fields import ObjectId
from superdesk.core.resources.validators import validate_not_empty, validate_data_relation_async


class ContentListType(str, enum.Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    BUCKET = "bucket"


class ContentList(ResourceModelWithObjectId):
    name: Annotated[str, validate_not_empty()]
    list_type: Annotated[ContentListType, Field(alias="type")]
    description: str | None = None
    limit: int | None = None
    cache_life_time: int | None = None
    filters: dict[str, Any] | None = None
    enabled: bool = True
    content_list_items_updated_at: datetime | None = None


class ContentListItem(ResourceModelWithObjectId):
    list_id: ObjectId
    content: Annotated[str, validate_data_relation_async("archive")]
    position: int | None = None
    sticky: bool = False
    sticky_position: int | None = None
    enabled: bool = True


class ContentListWebhook(ResourceModelWithObjectId):
    url: Annotated[str, validate_not_empty()]
    name: str | None = None
    enabled: bool = True
    # Webhooks fire for every content list by default; ids listed here are skipped.
    excluded_lists: list[ObjectId] = Field(default_factory=list)

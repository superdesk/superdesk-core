import enum
from typing import Any, Annotated
from datetime import datetime

from pydantic import AnyHttpUrl, BeforeValidator, Field, TypeAdapter

from superdesk.core.resources import BaseModel, ResourceModelWithObjectId
from superdesk.core.resources.fields import ObjectId
from superdesk.core.resources.validators import validate_not_empty, validate_data_relation_async

_http_url_adapter: TypeAdapter = TypeAdapter(AnyHttpUrl)

# Validates as an HTTP(S) URL and stores the WHATWG-canonical form (a bare
# domain gets a trailing slash: ``https://x.com`` → ``https://x.com/``), so
# equivalent spellings of the same endpoint can't coexist as duplicates. Kept
# a plain ``str`` so it stays serializable for MongoDB storage and Celery
# task arguments.
HttpUrlStr = Annotated[str, BeforeValidator(lambda value: str(_http_url_adapter.validate_python(value)))]


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


class ContentListItemAction(str, enum.Enum):
    ADD = "add"
    MOVE = "move"
    DELETE = "delete"


class ContentListBulkActionItem(BaseModel):
    action: ContentListItemAction
    content_id: Annotated[str, Field(alias="contentId")]
    position: int | None = None
    # ``None`` means the client omitted the field; a ``move`` then keeps the
    # item's stored sticky flag instead of resetting it.
    sticky: bool | None = None
    sticky_position: Annotated[int | None, Field(alias="stickyPosition")] = None


class ContentListBulkActions(BaseModel):
    """Payload of the content list items bulk PATCH endpoint.

    ``updated_at`` stays a plain string: the optimistic concurrency check
    compares it verbatim against the ``strftime(DATE_FORMAT)`` rendering the
    server handed out, so parsing it as a datetime would change precision and
    break the comparison.
    """

    items: list[ContentListBulkActionItem]
    updated_at: Annotated[str, Field(alias="updatedAt")]


class ContentListWebhook(ResourceModelWithObjectId):
    url: HttpUrlStr
    name: str | None = None
    enabled: bool = True
    # Webhooks fire for every content list by default; ids listed here are skipped.
    excluded_lists: list[ObjectId] = Field(default_factory=list)

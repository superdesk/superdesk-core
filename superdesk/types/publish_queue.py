from typing import Annotated
from enum import Enum, unique
from datetime import datetime

from superdesk.core.resources import ResourceModelWithObjectId, fields
from superdesk.core.resources.validators import validate_data_relation_async

from .subscribers import SubscriberDestination


@unique
class PublishQueueState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    RETRYING = "retrying"
    SUCCESS = "success"
    CANCELED = "canceled"
    ERROR = "error"
    FAILED = "failed"


class PublishQueueResource(ResourceModelWithObjectId):
    item_id: str
    publishing_action: str

    item_version: int
    formatted_item: str

    state: PublishQueueState | None = None  # If None, will allow the resource service to choose the state
    item_encoding: str | None = None
    encoded_item_id: str | None = None

    subscriber_id: Annotated[fields.ObjectId, validate_data_relation_async("subscribers")]

    codes: list[str] | None = None
    destination: SubscriberDestination | None = None

    published_in_package: str | None = None
    published_seq_num: int | None = None

    # publish_schedule is to indicate the item schedule datetime.
    # entries in the queue are created after schedule has elapsed.
    publish_schedule: datetime | None = None
    unique_name: str | None = None
    content_type: str | None = None
    headline: str | None = None
    transmit_started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    # to indicate the queue item is moved to legal
    # True is set after state of the item is success, cancelled or failed. For other state it is false
    moved_to_legal: bool = False
    retry_attempt: int = 0
    next_retry_attempt_at: datetime | None = None
    ingest_provider: Annotated[fields.ObjectId | None, validate_data_relation_async("ingest_providers")] = None
    associated_items: list[dict] | None = None
    priority: bool | None = None

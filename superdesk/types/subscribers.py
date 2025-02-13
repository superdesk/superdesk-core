from typing import Annotated
from typing_extensions import Self
from datetime import datetime
from enum import Enum, unique

from pydantic import Field

from superdesk.core.resources import ResourceModelWithObjectId, Dataclass, fields
from superdesk.core.resources.validators import (
    validate_data_relation_async,
    validate_iunique_value_async,
    validate_email,
    validate_not_empty,
)


class SubscriberSequenceSettings(Dataclass):
    min: int
    max: int


class SubscriberLastClosed(Dataclass):
    closed_at: datetime
    message: str
    closed_by: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None


class SubscriberDestination(Dataclass):
    name: Annotated[str, validate_not_empty()]
    format: str
    delivery_type: str
    _id: str | None = None
    preview_endpoint_url: str | None = None
    config: dict | None = None


@unique
class SubscriberType(str, Enum):
    DIGITAL = "digital"
    WIRE = "wire"
    ALL = "all"


class SubscribersResource(ResourceModelWithObjectId):
    name: Annotated[str, validate_not_empty(), validate_iunique_value_async("subscribers", "name")]
    subscriber_type: SubscriberType
    email: Annotated[str, validate_not_empty(), validate_email(multi=True)]
    media_type: str | None = None
    sequence_num_settings: SubscriberSequenceSettings | None = None

    is_active: bool = False
    is_targetable: bool = True

    critical_errors: dict[str, bool] | None = None
    last_closed: SubscriberLastClosed | None = None
    destinations: list[SubscriberDestination] | None = None
    products: Annotated[list[fields.ObjectId] | None, validate_data_relation_async("products")] = None
    codes: str | None = None
    global_filters: dict[str, bool] | None = None
    content_api_token: str | None = None
    api_products: Annotated[list[fields.ObjectId] | None, validate_data_relation_async("products")] = None
    is_async: Annotated[bool | None, Field(alias="async")] = None
    priority: bool | None = None

    init_version: int | None = None

    def is_digital(self) -> bool:
        return self.subscriber_type in {SubscriberType.DIGITAL, SubscriberType.ALL}

    @classmethod
    def filter_digital(cls, subscribers: list[Self]) -> list[Self]:
        return [subscriber for subscriber in subscribers if subscriber.is_digital()]

    @classmethod
    def filter_non_digital(cls, subscribers: list[Self]) -> list[Self]:
        return [subscriber for subscriber in subscribers if not subscriber.is_digital()]

    @classmethod
    async def get_names(cls, lookup: dict) -> list[str]:
        cursor = await cls.get_service().search(lookup)
        return [subscriber.name async for subscriber in cursor]

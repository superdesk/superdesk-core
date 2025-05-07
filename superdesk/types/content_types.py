# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import logging
from typing import Annotated, Any, cast
from typing_extensions import LiteralString

from pydantic import Field
from quart_babel import gettext

from superdesk.core.resources import ResourceModel, fields, Dataclass
from superdesk.core.resources.validators import validate_data_relation_async, validate_iunique_value_async

from pydantic_core import PydanticCustomError

from superdesk.core.resources.validators import AsyncValidator

logger = logging.getLogger(__name__)


async def _validate_content_type(item: ResourceModel, _) -> None:
    item = cast(ContentTypesResourceModel, item)
    if not item.content_type or item.content_type.lower() == "text":
        return
    if await ContentTypesResourceModel.get_service().count({"type": item.content_type, "_id": {"$ne": item.id}}) > 0:
        msg: LiteralString = gettext("Only 1 instance is allowed.")
        raise PydanticCustomError("unique", msg)


validate_content_type = AsyncValidator(_validate_content_type)


class WidgetConfig(Dataclass):
    widget_id: str
    is_displayed: bool


class ContentTypesResourceModel(ResourceModel):
    content_type: Annotated[str | None, validate_content_type, Field(alias="type")] = None
    label: Annotated[str, validate_iunique_value_async("content_types", "label")]
    icon: str | None = None
    description: str | None = None
    content_schema: dict[str, Any] = Field(default_factory=dict, alias="schema")
    editor: dict[str, Any] = Field(default_factory=dict)
    widgets_config: list[WidgetConfig] = Field(default_factory=list)
    priority: int = 0
    enabled: bool = False
    is_used: bool = False
    embeddable: bool = False
    created_by: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None
    updated_by: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None
    init_version: int | None = None
    output_name: str | None = None

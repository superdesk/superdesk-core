# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from enum import Enum, unique
import logging
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field
from quart_babel import gettext as _

from superdesk.core.resources import ResourceModel
from superdesk.core.resources.model import Dataclass, ResourceModel
from superdesk.core.resources.validators import validate_maxlength

logger = logging.getLogger(__name__)


class Tag(Dataclass):
    text: str


class Item(BaseModel):
    name: str
    qcode: str
    is_active: bool = True


class DateShortcut(Dataclass):
    value: int
    term: str
    label: str


class CustomFieldConfig(Dataclass):
    increment_steps: list[int]
    initial_offset_minutes: int


@unique
class CVAccessType(str, Enum):
    MANAGEABLE = "manageable"
    UNMANAGEABLE = "unmanageable"


@unique
class SelectionType(str, Enum):
    SINGLE_SELECTION = "single selection"
    MULTI_SELECTION = "multi selection"
    DO_NOT_SHOW = "do not show"


class VocabulariesResourceModel(ResourceModel):
    display_name: str
    description: str | None = None
    helper_text: Annotated[str | None, validate_maxlength(120)] = None
    tags: list[Tag] | None = None
    popup_width: int | None = None
    management_type: Annotated[CVAccessType, Field(alias="type")]
    items: list[Item]
    selection_type: SelectionType | None = None
    read_only: bool | None = None
    schema_field: str | None = None
    dependent: bool = False
    service: dict[str, int] = Field(default_factory=dict)
    priority: int = 0
    unique_field: str | None = None
    schema: dict[str, dict]
    field_type_: str | None = None
    field_options_: dict[str, Any] = Field(default_factory=dict)
    init_version: int = 0
    preffered_items: bool = False
    disable_entire_category_selection: bool = False
    date_shortcuts: list[DateShortcut] | None = None
    custom_field_type: str | None = None
    custom_field_config: CustomFieldConfig | None = None
    translations: dict[str, dict[str, Any]] = Field(default_factory=dict)

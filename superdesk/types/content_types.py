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
from typing import Annotated, Any

from pydantic import Field
from quart_babel import gettext as _

from superdesk.core.resources import ResourceModel
from superdesk.core.resources.model import ResourceModel
from superdesk.core.resources.validators import validate_iunique_value_async

logger = logging.getLogger(__name__)


class WidgetConfig(ResourceModel):
    widget_id: str
    is_displayed: bool


class ContentTypes(ResourceModel):
    type_: Annotated[str | None, Field(alias="type")]
    label: Annotated[str, validate_iunique_value_async("content_types", "label")]
    icon: str
    description: str
    schema: dict[str, Any] = Field(default_factory=dict)  # type: ignore[assignment]
    editor: dict[str, Any] = Field(default_factory=dict)
    widgets_config: list[WidgetConfig] = Field(default_factory=list)
    priority: int = 0
    enabled: bool = False
    is_used: bool = False
    embeddable: bool = False
    created_by: str | None = None
    updated_by: str | None = None
    init_version: int
    output_name: str | None = None

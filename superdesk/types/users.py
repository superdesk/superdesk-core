# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk Users"""


from datetime import datetime
from enum import Enum, unique
from typing import Annotated, Any

from pydantic import Field
from superdesk.core.resources import ResourceModel, fields
from superdesk.core.resources.fields import ObjectId
from superdesk.core.resources.validators import validate_unique_value_async, validate_data_relation_async


@unique
class UserTypeEnum(str, Enum):
    USER = "user"
    ADMINISTRATOR = "administrator"
    EXTERNAL = "external"


class UsersResourceModel(ResourceModel):
    username: Annotated[fields.Keyword, validate_unique_value_async("users", "username")]
    password: str = Field(min_length=5)
    password_changed_on: datetime | None = None
    first_name: str
    last_name: str
    display_name: str
    email: Annotated[fields.Keyword, validate_unique_value_async("users", "email")]
    phone: str | None = None
    job_title: str | None = None
    biography: str | None = None
    facebook: str | None = None
    instagram: str | None = None
    twitter: str | None = None
    jid: Annotated[fields.Keyword, validate_unique_value_async("users", "jid")] | None = None
    language: str | None = None
    user_info: dict[str, Any] = Field(default_factory=dict)
    picture_url: str | None = None
    avatar: Annotated[ObjectId, validate_data_relation_async("upload")] | None = None
    avatar_renditions: dict[str, Any] | None = Field(default=None)
    role: Annotated[ObjectId, validate_data_relation_async("roles")]
    privileges: dict[str, Any] = Field(default_factory=dict)
    workspace: dict[str, Any] = Field(default_factory=dict)
    user_type: UserTypeEnum = Field(default=UserTypeEnum.USER)
    is_support: bool = Field(default=False)
    is_author: bool = Field(default=True)
    private: bool | None = Field(default=False)
    is_active: bool = Field(default=True)
    is_enabled: bool = Field(default=True)
    needs_activation: bool = Field(default=True)
    # Default desk of the user, selected when logged-in.
    desk: Annotated[ObjectId, validate_data_relation_async("desks")] | None = None
    # Used for putting a sign-off on the content when it's created/updated except kill
    sign_off: str | None = None
    byline: str | None = None
    # List to hold invisible stages.
    # This field is updated under the following scenarios:
    # 1. Stage visible flag is updated
    # 2. Desk membership is modified
    # 3. New user is created
    invisible_stages: list | None = Field(default=None)
    # If Slack notifications are configured and enabled for the user
    # the Slack username is stored here.
    slack_username: str | None = None
    # The Slack user id is stored here to avoid repeat look ups
    slack_user_id: str | None = None
    session_preferences: dict[str, Any] = Field(default_factory=dict)
    user_preferences: dict[str, Any] = Field(default_factory=dict)
    last_activity_at: datetime | None = None

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Callable, Any, Awaitable, Union
import re

from pydantic import AfterValidator

from .fields import ObjectId


def validate_email() -> AfterValidator:
    """Validates that the value is a valid email address"""

    def _validate_email(value: str) -> str:
        # it's tricky to write proper regex for email validation, so we
        # should use simple one, or use libraries like
        # - https://pypi.python.org/pypi/email_validator
        # - https://pypi.python.org/pypi/pyIsEmail
        # given that admins are usually create users, not users by themself,
        # probably just check for @ is enough
        # https://davidcel.is/posts/stop-validating-email-addresses-with-regex/
        if not re.match(".+@.+", value, re.IGNORECASE):
            raise ValueError(f"Invalid email: {value}")
        return value

    return AfterValidator(_validate_email)


MinMaxAcceptedTypes = Union[str, list, int, float, None]


def validate_minlength(min_length: int) -> AfterValidator:
    """Validates that the value has a minimum length"""

    def _validate_minlength(value: MinMaxAcceptedTypes) -> MinMaxAcceptedTypes:
        if isinstance(value, (type(""), list)):
            if len(value) < min_length:
                raise ValueError(f"Invalid minlength: {value}")
        elif isinstance(value, (int, float)):
            if value < min_length:
                raise ValueError(f"Invalid minlength: {value}")
        return value

    return AfterValidator(_validate_minlength)


def validate_maxlength(max_length: int) -> AfterValidator:
    """Validates that the value has a maximum length (strings or arrays)"""

    def _validate_maxlength(value: MinMaxAcceptedTypes) -> MinMaxAcceptedTypes:
        if isinstance(value, (type(""), list)):
            if len(value) > max_length:
                raise ValueError(f"Invalid maxlength: {value}")
        elif isinstance(value, (int, float)):
            if value > max_length:
                raise ValueError(f"Invalid maxlength: {value}")
        return value

    return AfterValidator(_validate_maxlength)


class AsyncValidator:
    func: Callable[["ResourceModel", Any], Awaitable[None]]

    def __init__(self, func: Callable[["ResourceModel", Any], Awaitable[None]]):
        self.func = func


def validate_data_relation_async(resource_name: str, external_field: str = "_id") -> AsyncValidator:
    """Validate the ID on the resource points to an existing resource

    :param resource_name: The name of the resource type the ID points to
    :param external_field: The field used to find the resource
    """

    async def validate_resource_exists(item: ResourceModel, item_id: Union[str, ObjectId, None]) -> None:
        if item_id is None:
            return

        from superdesk.core.app import get_current_async_app

        app = get_current_async_app()
        resource_config = app.resources.get_config(resource_name)
        collection = app.mongo.get_collection_async(resource_config.name)
        if not await collection.find_one({external_field: item_id}):
            raise ValueError(f"Resource '{resource_name}' with ID '{item_id}' does not exist")

    return AsyncValidator(validate_resource_exists)


def validate_unique_value_async(resource_name: str, field_name: str) -> AsyncValidator:
    """Validate that the field is unique in the resource (case-sensitive)

    :param resource_name: The name of the resource where the field must be unique
    :param field_name: The name of the field where the field must be unique
    """

    async def validate_unique_value_in_resource(item: ResourceModel, name: Union[str, None]) -> None:
        if name is None:
            return

        from superdesk.core.app import get_current_async_app

        app = get_current_async_app()
        resource_config = app.resources.get_config(resource_name)
        collection = app.mongo.get_collection_async(resource_config.name)

        if await collection.find_one({field_name: name, "_id": {"$ne": item.id}}):
            raise ValueError(f"Resource '{resource_name}' with '{field_name}=={name}' already exists")

    return AsyncValidator(validate_unique_value_in_resource)


def validate_iunique_value_async(resource_name: str, field_name: str) -> AsyncValidator:
    """Validate that the field is unique in the resource (case-insensitive)

    :param resource_name: The name of the resource where the field must be unique
    :param field_name: The name of the field where the field must be unique
    """

    async def validate_iunique_value_in_resource(item: ResourceModel, name: Union[str, None]) -> None:
        if name is None:
            return

        from superdesk.core.app import get_current_async_app

        app = get_current_async_app()
        resource_config = app.resources.get_config(resource_name)
        collection = app.mongo.get_collection_async(resource_config.name)

        pattern = "^{}$".format(re.escape(name.strip()))
        if await collection.find_one({field_name: re.compile(pattern, re.IGNORECASE), "_id": {"$ne": item.id}}):
            raise ValueError(f"Resource '{resource_name}' with '{field_name}=={name}' already exists")

    return AsyncValidator(validate_iunique_value_in_resource)


from .model import ResourceModel  # noqa: E402

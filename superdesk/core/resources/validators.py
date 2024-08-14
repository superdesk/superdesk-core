# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Callable, Any, Awaitable, Dict
import re
import logging

from quart_babel import gettext
from pydantic import AfterValidator, ValidationError
from pydantic_core import PydanticCustomError
from bson import ObjectId


logger = logging.getLogger(__name__)


EmailValueType = str | list[str] | None


def validate_email() -> AfterValidator:
    """Validates that the value is a valid email address"""

    def _validate_email(value: EmailValueType) -> EmailValueType:
        if value is None:
            return None
        elif isinstance(value, list):
            for email in value:
                _validate_email(email)
        elif not re.match(".+@.+", value, re.IGNORECASE):
            # it's tricky to write proper regex for email validation, so we
            # should use simple one, or use libraries like
            # - https://pypi.python.org/pypi/email_validator
            # - https://pypi.python.org/pypi/pyIsEmail
            # given that admins are usually create users, not users by themself,
            # probably just check for @ is enough
            # https://davidcel.is/posts/stop-validating-email-addresses-with-regex/
            raise PydanticCustomError("email", gettext("Invalid email address"))
        return value

    return AfterValidator(_validate_email)


MinMaxValueType = str | int | float | list[str] | list[int] | list[float] | None


def validate_minlength(min_length: int, validate_list_elements: bool = False) -> AfterValidator:
    """Validates that the value has a minimum length

    :param min_length: The minimum length of the value
    :param validate_list_elements: Whether to validate the elements in the list or the list length
    """

    def _validate_minlength(value: MinMaxValueType) -> MinMaxValueType:
        if isinstance(value, list) and validate_list_elements:
            for val in value:
                _validate_minlength(val)
        elif isinstance(value, (type(""), list)):
            if len(value) < min_length:
                raise PydanticCustomError("minlength", gettext("Not enough"))
        elif isinstance(value, (int, float)):
            if value < min_length:
                raise PydanticCustomError("min_length", gettext("Too short"))
        return value

    return AfterValidator(_validate_minlength)


def validate_maxlength(max_length: int, validate_list_elements: bool = False) -> AfterValidator:
    """Validates that the value has a maximum length (strings or arrays)

    :param max_length: The maximum length of the value
    :param validate_list_elements: Whether to validate the elements in the list or the list length
    """

    def _validate_maxlength(value: MinMaxValueType) -> MinMaxValueType:
        if isinstance(value, list) and validate_list_elements:
            for val in value:
                _validate_maxlength(val)
        elif isinstance(value, (type(""), list)):
            if len(value) > max_length:
                raise PydanticCustomError("maxlength", gettext("Too many"))
        elif isinstance(value, (int, float)):
            if value > max_length:
                raise PydanticCustomError("maxlength", gettext("Too short"))
        return value

    return AfterValidator(_validate_maxlength)


class AsyncValidator:
    func: Callable[["ResourceModel", Any], Awaitable[None]]

    def __init__(self, func: Callable[["ResourceModel", Any], Awaitable[None]]):
        self.func = func


DataRelationValueType = str | ObjectId | list[str] | list[ObjectId] | None


def validate_data_relation_async(
    resource_name: str, external_field: str = "_id", convert_to_objectid: bool = False
) -> AsyncValidator:
    """Validate the ID on the resource points to an existing resource

    :param resource_name: The name of the resource type the ID points to
    :param external_field: The field used to find the resource
    :param convert_to_objectid: If True, will convert the ID to an ObjectId instance
    """

    async def validate_resource_exists(item: ResourceModel, item_id: DataRelationValueType) -> None:
        if item_id is None:
            return
        elif isinstance(item_id, list):
            for value in item_id:
                await validate_resource_exists(item, value)
        else:
            if convert_to_objectid:
                item_id = ObjectId(item_id)

            from superdesk.core import get_current_async_app

            app = get_current_async_app()
            try:
                resource_config = app.resources.get_config(resource_name)
                collection = app.mongo.get_collection_async(resource_config.name)
                if not await collection.find_one({external_field: item_id}):
                    raise PydanticCustomError(
                        "data_relation",
                        gettext("Resource '{resource_name}' with ID '{item_id}' does not exist"),
                        dict(
                            resource_name=resource_name,
                            item_id=item_id,
                        ),
                    )
            except KeyError:
                # Resource is not registered with async resources
                # Try legacy resources instead
                from superdesk import get_resource_service

                service = get_resource_service(resource_name)
                item = service.find_one(req=None, **{external_field: item_id})
                if item is None:
                    raise PydanticCustomError(
                        "data_relation",
                        gettext("Resource '{resource_name}' with ID '{item_id}' does not exist"),
                        dict(
                            resource_name=resource_name,
                            item_id=item_id,
                        ),
                    )

    return AsyncValidator(validate_resource_exists)


UniqueValueType = str | list[str] | None


def validate_unique_value_async(resource_name: str, field_name: str) -> AsyncValidator:
    """Validate that the field is unique in the resource (case-sensitive)

    :param resource_name: The name of the resource where the field must be unique
    :param field_name: The name of the field where the field must be unique
    """

    async def validate_unique_value_in_resource(item: ResourceModel, name: UniqueValueType) -> None:
        if name is None:
            return

        from superdesk.core import get_current_async_app

        app = get_current_async_app()
        resource_config = app.resources.get_config(resource_name)
        collection = app.mongo.get_collection_async(resource_config.name)

        query = {"_id": {"$ne": item.id}, field_name: {"$in": name} if isinstance(name, list) else name}
        if await collection.find_one(query):
            raise PydanticCustomError("unique", gettext("Value must be unique"))

    return AsyncValidator(validate_unique_value_in_resource)


def validate_iunique_value_async(resource_name: str, field_name: str) -> AsyncValidator:
    """Validate that the field is unique in the resource (case-insensitive)

    :param resource_name: The name of the resource where the field must be unique
    :param field_name: The name of the field where the field must be unique
    """

    async def validate_iunique_value_in_resource(item: ResourceModel, name: UniqueValueType) -> None:
        if name is None:
            return

        from superdesk.core import get_current_async_app

        app = get_current_async_app()
        resource_config = app.resources.get_config(resource_name)
        collection = app.mongo.get_collection_async(resource_config.name)

        query = {
            "_id": {"$ne": item.id},
            field_name: (
                {"$in": [re.compile("^{}$".format(re.escape(value.strip())), re.IGNORECASE) for value in name]}
                if isinstance(name, list)
                else re.compile("^{}$".format(re.escape(name.strip())), re.IGNORECASE)
            ),
        }

        if await collection.find_one(query):
            raise PydanticCustomError("unique", gettext("Value must be unique"))

    return AsyncValidator(validate_iunique_value_in_resource)


def convert_pydantic_validation_error_for_response(validation_error: ValidationError) -> Dict[str, Any]:
    return {
        "_status": "ERR",
        "_error": {"code": 403, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
        "_issues": get_field_errors_from_pydantic_validation_error(validation_error),
    }


def get_field_errors_from_pydantic_validation_error(validation_error: ValidationError) -> Dict[str, Dict[str, str]]:
    issues: Dict[str, Dict[str, str]] = {}
    for error in validation_error.errors():
        try:
            field = ".".join([str(loc) for loc in error["loc"]])
            issues.setdefault(field, {})
            if error["type"] == "missing":
                # Validations provided by Pydantic
                issues[field]["required"] = gettext("Field is required")
            else:
                issues[field][error["type"]] = error["msg"]
        except (KeyError, TypeError, ValueError) as error:
            logger.warning(error)

    return issues


from .model import ResourceModel  # noqa: E402

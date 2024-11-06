# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import TYPE_CHECKING, Annotated

from typing_extensions import TypeVar, Generic, ClassVar, Dict, Any, cast, Type, Callable

from datetime import datetime
from pydantic_core import core_schema
from pydantic import (
    GetJsonSchemaHandler,
    GetCoreSchemaHandler,
    WithJsonSchema,
    Field,
    ConfigDict,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic.dataclasses import dataclass
from bson import ObjectId as BsonObjectId

DefaultModelConfig = ConfigDict(
    arbitrary_types_allowed=True,
    validate_assignment=True,  # Revalidate on field assignment
    populate_by_name=True,
)


def get_core_schema_from_type(class_type: Type) -> core_schema.CoreSchema:
    schema_mapping: Dict[Type, Callable[[], core_schema.CoreSchema]] = {
        str: core_schema.str_schema,
        int: core_schema.int_schema,
        float: core_schema.float_schema,
        bool: core_schema.bool_schema,
        bytes: core_schema.bytes_schema,
        datetime: core_schema.datetime_schema,
    }

    try:
        return schema_mapping[class_type]()
    except KeyError:
        raise RuntimeError(f"Unsupported base class type: {class_type}")


class BaseCustomField:
    """Base class used to define custom fields"""

    #: Base Schema to be used for this field
    json_schema: ClassVar[JsonSchemaValue] = {}

    #: Elasticsearch mapping to be applied for this field
    elastic_mapping: ClassVar[Dict[str, Any]]

    #: The core python data type
    core_type: ClassVar[Type] = str

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _schema: core_schema.CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {
            **(cls.json_schema or get_core_schema_from_type(cls.core_type)),
            "elastic_mapping": cls.elastic_mapping,
        }


CustomStringFieldType = TypeVar("CustomStringFieldType", default=str)


class CustomStringField(Generic[CustomStringFieldType], BaseCustomField):
    """Base class used to define custom string fields (such as ObjectId)"""

    json_schema: ClassVar[JsonSchemaValue] = {"type": "string"}

    @classmethod
    def _validate(cls, value: str) -> CustomStringFieldType:
        return cast(CustomStringFieldType, value)

    @classmethod
    def serialise_value(cls, value: Any, info: core_schema.FieldSerializationInfo):
        return str(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls._validate),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(cls.core_type),
                    from_str_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialise_value,
                info_arg=True,
            ),
        )


if TYPE_CHECKING:
    Keyword = Annotated[str, ...]
    TextWithKeyword = Annotated[str, ...]
    HTML = Annotated[str, ...]
    ObjectId = Annotated[BsonObjectId, ...]
else:

    class Keyword(CustomStringField, str):
        """Elasticsearch keyword field"""

        elastic_mapping = {"type": "keyword"}

    class TextWithKeyword(CustomStringField):
        """Elasticsearch text field with a keyword sub-field

        Additionally, adds ``html_field_analyzer`` analyzer, as to keep with the same config
        defined in original superdesk.resource.text_with_keyword mapping
        """

        elastic_mapping = {
            "type": "text",
            "fields": {"keyword": {"type": "keyword"}},
            "analyzer": "html_field_analyzer",
        }

    class HTML(str, CustomStringField):
        """Elasticsearch HTML field, used the 'html_field_analyzer' analyzer"""

        json_schema = {"type": "string", "format": "html"}
        elastic_mapping = {"type": "text", "analyzer": "html_field_analyzer"}

    class ObjectId(BsonObjectId, CustomStringField[BsonObjectId]):
        """Elasticsearch ObjectId field"""

        json_schema = {"type": "string", "format": "objectid"}
        elastic_mapping = {"type": "text"}
        core_type = BsonObjectId

        @classmethod
        def _validate(cls, value: str) -> BsonObjectId:
            return BsonObjectId(value)

        @classmethod
        def serialise_value(cls, value: Any, info: core_schema.FieldSerializationInfo):
            return str(value) if not (info.context or {}).get("use_objectid") else BsonObjectId(value)


def elastic_mapping(mapping: dict[str, Any]) -> WithJsonSchema:
    return Field(json_schema_extra={"elastic_mapping": mapping})


def keyword_mapping() -> WithJsonSchema:
    return Field(json_schema_extra={"elastic_mapping": {"type": "keyword"}})


def dynamic_mapping() -> WithJsonSchema:
    return Field(json_schema_extra={"elastic_mapping": {"type": "object", "dynamic": True}})


def mapping_disabled(data_type: str) -> WithJsonSchema:
    return Field(json_schema_extra={"elastic_mapping": {"type": data_type, "enabled": False}})


def nested_list(include_in_parent: bool = False) -> WithJsonSchema:
    """Field modifier, to enabled nested in Elasticsearch for the field

    Example usage::

        from typing import Annotated
        from typing_extensions import TypedDict
        from superdesk.core.resources import ResourceModel, fields, dataclass

        @dataclass
        class Subjects:
            qcode: str
            name: str
            scheme: str | None = None

        class Content(ResourceModel):
            ...
            subjects: Annotated[list[Subjects], fields.nested_list()]
    """

    return Field(json_schema_extra={"nested": True, "include_in_parent": include_in_parent})


def not_indexed() -> WithJsonSchema:
    return Field(json_schema_extra={"elastic_mapping": {"type": "text", "index": False}})


@dataclass(config=dict(validate_assignment=True))
class Geopoint(BaseCustomField):
    """Elasticsearch geo_point field"""

    elastic_mapping = {"type": "geo_point"}
    json_schema = {
        "type": "object",
        "required": ["lat", "lon"],
        "properties": {
            "lat": {
                "type": "number",
                "title": "Latitude",
            },
            "lon": {
                "type": "number",
                "title": "Longitude",
            },
        },
    }

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing_extensions import TypeVar, Generic, ClassVar, Dict, Any, cast, Type

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
    if class_type == str:
        return core_schema.str_schema()
    elif class_type == int:
        return core_schema.int_schema()
    elif class_type == float:
        return core_schema.float_schema()
    elif class_type == bool:
        return core_schema.bool_schema()
    elif class_type == bytes:
        return core_schema.bytes_schema()
    elif class_type == datetime:
        return core_schema.datetime_schema()
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
            serialization=core_schema.plain_serializer_function_ser_schema(lambda instance: str(instance)),
        )


class Keyword(CustomStringField, str):
    """Elasticsearch keyword field"""

    elastic_mapping = {"type": "keyword"}


class TextWithKeyword(CustomStringField):
    """Elasticsearch text field with a keyword sub-field"""

    elastic_mapping = {
        "type": "text",
        "fields": {"keyword": {"type": "keyword"}},
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


def nested_list() -> WithJsonSchema:
    """Field modifier, to enabled nested in Elasticsearch for the field

    Example usage::

        from typing import List
        from typing_extensions import Annotated, TypedDict
        from superdesk.core.resources import ResourceModel, fields, dataclass

        @dataclass
        class Subjects:
            qcode: str
            name: str
            scheme: Optional[str] = None

        class Content(ResourceModel):
            ...
            subjects: Annotated[List[Subjects], fields.nested_list()]
    """

    return Field(json_schema_extra={"nested": True})


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

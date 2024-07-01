# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Optional
import logging

from ..resources import ResourceModel

logger = logging.getLogger(__name__)


def _get_field_type_from_json_schema(
    schema: Dict[str, Any], props: Dict[str, Any], parent_props: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    if props.get("elastic_mapping"):
        return props["elastic_mapping"]

    if props.get("$ref"):
        type_name = props["$ref"].replace("#/$defs/", "")
        type_schema = schema["$defs"][type_name]

        if type_schema.get("elastic_mapping"):
            return type_schema["elastic_mapping"]

        properties: Dict[str, Any] = {}
        for type_field, type_props in type_schema["properties"].items():
            type_field_type = _get_field_type_from_json_schema(schema, type_props)
            if type_field_type is not None:
                properties[type_field] = type_field_type
        return {"properties": properties}

    if props.get("anyOf"):
        # Get the first non-null (optional) type
        any_of = [val for val in props["anyOf"] if val.get("type") != "null"]
        if len(any_of) == 1:
            return _get_field_type_from_json_schema(schema, any_of[0], props)
        else:
            # No non-null type found, unable to determine the value type
            return None

    try:
        field_type: str = props["type"]
    except KeyError:
        # Unable to determine the field type if none is provided
        return None

    if field_type == "string":
        field_format = props.get("format")
        if field_format == "date-time":
            return {"type": "date"}
        elif field_format == "binary":
            return {"type": "binary"}  # Base64 string
        return {"type": "text"}
    elif field_type == "integer":
        return {"type": "integer"}
    elif field_type == "number":
        return {"type": "double"}
    elif field_type == "boolean":
        return {"type": "boolean"}
    elif field_type == "object":
        # Objects, unstructured dictionaries, are not supported.
        # So we will disable elastic mapping for this field
        return {"type": "object", "enabled": False}
        # return {"type": "flattened"}
    elif field_type == "array":
        try:
            mapping = _get_field_type_from_json_schema(schema, props["items"])
            if mapping is None:
                return None
            elif props.get("nested") or (parent_props is not None and parent_props.get("nested")):
                mapping["type"] = "nested"
            return mapping
        except KeyError:
            # If ``items`` is not defined, we cannot determine the type
            return None

    # Unknown type
    return None


def json_schema_to_elastic_mapping(json_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Construct an Elasticsearch mapping from an OpenAPI JSON schema.

    :param json_schema: OpenAPI JSON schema
    :return: Elastic mapping for use with an Elasticsearch index
    """

    properties: Dict[str, Any] = {}
    for field, props in json_schema["properties"].items():
        field_type = _get_field_type_from_json_schema(json_schema, props)
        if field_type is not None:
            properties[field] = field_type
    return {"properties": properties}


def get_elastic_mapping_from_model(
    name: str, model_class: type[ResourceModel], schema_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Constructs an Elasticsearch mapping from a ResourceModel

    :param name: The name of the resource
    :param model_class: The ResourceModel class
    :param schema_overrides: Overrides to be applied to the generated mapping
    :return: Elastic mapping for use with an ELasticsearch index
    """

    mapping = json_schema_to_elastic_mapping(model_class.model_json_schema(mode="serialization"))

    if schema_overrides is not None:
        logger.warning(f"Update {name} schema with custom data for fields")
        mapping["properties"].update(schema_overrides)

    # Remove ``_id`` field, as Elasticsearch already provides this for us
    mapping["properties"].pop("_id", None)
    return mapping

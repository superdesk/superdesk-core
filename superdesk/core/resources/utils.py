# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any, Literal, cast
from inspect import get_annotations

from pydantic.fields import FieldInfo
from quart_babel import gettext

from superdesk.core import json
from superdesk.utils import join_url_parts
from superdesk.core.types import SearchRequest, ProjectedFieldArg
from superdesk.errors import SuperdeskApiError
from superdesk.default_settings import strtobool


SYSTEM_FIELDS = {"_id", "_type", "_resource", "_etag"}


def get_projection_from_request(req: SearchRequest) -> tuple[bool, list[str]] | tuple[None, None]:
    """Convert request projection param into common format used by Mongo or Elastic

    :param req: A SearchRequest with an optional projection param
    :return: One of the following depending on expected projection:
        tuple[None, None] If no projection is to be used
        tuple[True, list[str]] When projection is to include fields
        tuple[False, list[str]] When projection is to exclude fields
    :raises SuperdeskApiError.badRequestError: If the projection param is of an unsupported type
    """

    projection_data: ProjectedFieldArg | None = None
    if req.args and req.args.get("projections"):
        projection_data = json.loads(req.args["projections"])
    elif req.projection:
        projection_data = req.projection

    if not projection_data:
        # No projection will be used
        return None, None
    elif isinstance(projection_data, (list, set)):
        # Projection: include these fields only
        return True, list(set(projection_data) | SYSTEM_FIELDS)
    elif isinstance(projection_data, dict):
        # Determine the projection type, ``True``: include fields, ``False``: exclude fields
        projection_types = set([strtobool(value) for value in projection_data.values()])

        if len(projection_types) > 1:
            # This request has both include and exclude projections, which is unsupported
            raise SuperdeskApiError.badRequestError(gettext("Cannot combine projections of different types"))

        if projection_types.pop():
            # Projection: include these fields only
            return True, list(
                set([field for field, value in projection_data.items() if value is True or value == 1]) | SYSTEM_FIELDS
            )
        else:
            # Projection: exclude these fields
            # Keep fields that should always be returned
            return False, list(
                set(
                    [
                        field
                        for field, value in projection_data.items()
                        if field not in SYSTEM_FIELDS and (value is False or value == 0)
                    ]
                )
            )

    raise SuperdeskApiError.badRequestError(gettext("invalid projection type"))


def combine_projection_args(
    *args: SearchRequest | ProjectedFieldArg | None,
) -> dict[str, Literal[True]] | dict[str, Literal[False]] | None:
    """Combines projection arguments into the 1, for use with either MongoDB or Elasticsearch

    This is used to combine projection config from a REST endpoint and projection argument from an API request argument.

    :raises SuperdeskApiError.badRequestError: If the projection type combines both include and exclude
    """
    projection: dict[bool, set[str]] = {False: set(), True: set()}

    for arg in args:
        if arg is None:
            continue

        projection_args: ProjectedFieldArg | None = None
        if isinstance(arg, SearchRequest):
            if arg.args and arg.args.get("projections"):
                projection_args = json.loads(arg.args["projections"])
            else:
                projection_args = arg.projection
        else:
            projection_args = arg

        if projection_args is None:
            continue
        elif isinstance(projection_args, (list, set)):
            projection[True].update(projection_args)
        elif isinstance(projection_args, dict):
            for key, value in projection_args.items():
                projection[strtobool(value)].add(key)

    num_includes = len(projection[True])
    num_excludes = len(projection[False])

    if num_includes and num_excludes:
        base_include_fields = set([field.split(".", 1)[0] for field in projection[True]])
        base_exclude_fields = set([field.split(".", 1)[0] for field in projection[False]])
        if base_include_fields.intersection(base_exclude_fields):
            raise SuperdeskApiError.badRequestError(
                gettext("Invalid projection: cannot include and exclude the same field")
            )

    if num_includes:
        return cast(dict[str, Literal[True]], {field: True for field in projection[True]})
    elif num_excludes:
        return cast(dict[str, Literal[False]], {field: False for field in projection[False]})
    else:
        return None


def get_model_aliased_fields(class_type: type) -> set[str]:
    """Returns the list of fields that are aliased

    For example::
        from superdesk.core.resources import dataclass, Dataclass

        @dataclass
        class TopicCreatedFilters(Dataclass):
            created_from: Annotated[str | None, Field(alias="from")] = None
            created_to: Annotated[str | None, Field(alias="to")] = None
            date_filter: str | None = None

        assert get_model_aliased_fields(TopicCreatedFilters) == set("created_from", "created_to")
    """

    annotations = get_annotations(class_type)
    aliased_fields: set[str] = set()

    for field_name, annotation in annotations.items():
        field_info: FieldInfo | None = next(
            (
                field_metadata
                for field_metadata in getattr(annotation, "__metadata__", [])
                if isinstance(field_metadata, FieldInfo)
            ),
            None,
        )
        if field_info is not None and field_info.alias:
            aliased_fields.add(field_name)

    return aliased_fields


def get_model_annotations(model_class: type["ResourceModel"]) -> dict[str, Any]:
    """Get all annotations from the model class and its parent classes.

    Traverses the class hierarchy up to (but not including) ResourceModel to collect all annotations.
    Parent class annotations are overridden by child class annotations.
    """
    from .model import ResourceModel

    annotations = {}

    # traverse class hierarchy in reverse MRO order (from parent to child)
    # so child class annotations override parent class annotations
    for base_class in reversed(model_class.__mro__):
        try:
            if base_class != ResourceModel and issubclass(base_class, ResourceModel):
                annotations.update(get_annotations(base_class))
        except (TypeError, AttributeError):
            # skip classes that don't support annotations or have attribute errors
            continue

    return annotations


def gen_url_for_related_resource(resource_name: str, item_id: str) -> str:
    """Generate a URL for a related resource.

    Uses the resource configuration to generate the proper URL, taking into account:
    1. Resource's configured URL (if different from resource name)
    2. Application URL prefix and API version
    """
    from superdesk.core import get_current_async_app, get_app_config

    # Default to resource_name as not all resources are async ready yet
    resource_url = resource_name

    try:
        app = get_current_async_app()
        resource_config = app.resources.get_config(resource_name)
        if resource_config.rest_endpoints is not None:
            resource_url = resource_config.rest_endpoints.url or resource_name
    except KeyError:
        pass

    url_prefix = get_app_config("URL_PREFIX") or ""
    api_version = get_app_config("API_VERSION") or ""

    return join_url_parts(url_prefix, api_version, resource_url, item_id)


from .model import ResourceModel  # noqa: E402

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from inspect import get_annotations

from pydantic.fields import FieldInfo
from quart_babel import gettext

from superdesk.core import json
from superdesk.core.types import SearchRequest, ProjectedFieldArg
from superdesk.errors import SuperdeskApiError


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
        if next(iter(projection_data.values()), None) in [True, 1]:
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

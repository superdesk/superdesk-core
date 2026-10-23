# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from eve import Eve


def init_app(app: Eve):
    """Initialize the `planning`, `events` and `assignments` API endpoints

    None of the endpoints are registered if `superdesk-planning` is not installed
    """

    try:
        from planning.prod_api import init_app as init_planning_app

        init_planning_app(app)
    except ImportError:
        pass
    else:
        from planning.events.events_schema import events_schema
        from planning.planning.planning_schema import planning_schema
        from planning.assignments.assignments import assignments_schema

        # These read-only endpoints omit the full schemas from Eve's DOMAIN.
        schemas = app.config.setdefault("_PRODAPI_RESPONSE_SCHEMAS", {})
        schemas.update(
            events=events_schema,
            planning=planning_schema,
            assignments=assignments_schema,
            events_history={"update": {"type": "dict", "schema": events_schema}},
        )
        assignment_link = {"type": "dict", "schema": {"scheduled": {"type": "datetime"}}}
        links = {
            "type": "dict",
            "schema": {
                "assignment": assignment_link,
                "assignments": {"type": "list", "schema": assignment_link},
            },
        }
        for resource in ("archive", "events", "planning", "assignments"):
            schemas[resource] = {**schemas.get(resource, {}), "_links": links}

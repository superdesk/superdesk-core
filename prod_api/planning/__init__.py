# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .services import PlanningService, EventsService, AssignmentsService, EventsHistoryService, EventsFilesService
from .resources import PlanningResource, EventsResource, AssignmentsResource, EventsHistoryResource, EventsFilesResource


def init_app(app):
    """Initialize the `planning`, `events` and `assignments` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    planning_service = PlanningService(datasource="planning", backend=superdesk.get_backend())
    PlanningResource(endpoint_name="planning", app=app, service=planning_service)

    events_service = EventsService(datasource="events", backend=superdesk.get_backend())
    EventsResource(endpoint_name="events", app=app, service=events_service)

    assignments_service = AssignmentsService(datasource="assignments", backend=superdesk.get_backend())
    AssignmentsResource(endpoint_name="assignments", app=app, service=assignments_service)

    events_history_service = EventsHistoryService(datasource="events_history", backend=superdesk.get_backend())
    EventsHistoryResource(endpoint_name="events_history", app=app, service=events_history_service)

    events_files_service = EventsFilesService(datasource="events_files", backend=superdesk.get_backend())
    EventsFilesResource(endpoint_name="events_files", app=app, service=events_files_service)

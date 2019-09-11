# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .services import PlanningService, EventsService
from .resources import PlanningResource, EventsResource


def init_app(app):
    """Initialize the `planning` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    planning_service = PlanningService(datasource='planning', backend=superdesk.get_backend())
    PlanningResource(endpoint_name='planning', app=app, service=planning_service)

    events_service = EventsService(datasource='events', backend=superdesk.get_backend())
    EventsResource(endpoint_name='events', app=app, service=events_service)

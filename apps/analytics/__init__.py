# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from apps.analytics.activity_reports import ActivityReportResource, ActivityReportService
from apps.analytics.saved_activity_reports import SavedActivityReportResource, \
    SavedActivityReportService


def init_app(app):
    endpoint_name = 'activity_reports'
    service = ActivityReportService(endpoint_name, backend=superdesk.get_backend())
    ActivityReportResource(endpoint_name, app=app, service=service)

    endpoint_name = 'saved_activity_reports'
    service = SavedActivityReportService(endpoint_name, backend=superdesk.get_backend())
    SavedActivityReportResource(endpoint_name, app=app, service=service)

    superdesk.privilege(name='activity_reports', label='Activity Report View',
                        description='User can view activity reports.')

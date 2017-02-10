# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.export.resource import ExportResource
from apps.export.service import ExportService
import superdesk


def init_app(app):
    endpoint_name = 'export'
    service = ExportService(endpoint_name, backend=superdesk.get_backend())
    ExportResource(endpoint_name, app=app, service=service)
    superdesk.privilege(name='content_export', label='Content export', description='Content export')

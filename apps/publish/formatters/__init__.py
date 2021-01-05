# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_backend
from apps.publish.formatters.service import FormattersService
from apps.publish.formatters.resource import FormattersResource


def init_app(app):
    endpoint_name = "formatters"
    service = FormattersService(endpoint_name, backend=get_backend())
    FormattersResource(endpoint_name, app=app, service=service)

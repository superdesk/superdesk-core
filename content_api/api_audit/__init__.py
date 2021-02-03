# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .resource import ApiAuditResource
from .service import ApiAuditService


def init_app(app):
    """
    Initialise the auditing of the API
    :param app:
    :return:
    """
    endpoint_name = "api_audit"

    service = ApiAuditService(endpoint_name, backend=superdesk.get_backend())
    ApiAuditResource(endpoint_name, app=app, service=service)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from content_api.companies.resource import CompaniesResource
import superdesk
from superdesk.services import BaseService


def init_app(app):
    endpoint_name = "companies"
    service = BaseService(endpoint_name, backend=superdesk.get_backend())
    CompaniesResource(endpoint_name, app=app, service=service)

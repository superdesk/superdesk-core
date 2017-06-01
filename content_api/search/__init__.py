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
from .service import SearchService
from .resource import SearchResource


def init_app(app):
    endpoint_name = 'search_capi'
    service = SearchService(endpoint_name, backend=superdesk.get_backend())
    SearchResource(endpoint_name, app=app, service=service)
    superdesk.privilege(name=endpoint_name, label='Content API Search', description='Content API Search')

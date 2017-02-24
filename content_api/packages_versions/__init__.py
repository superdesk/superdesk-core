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
from .service import PackagesVersionsService
from .resource import PackagesVersionsResource


def init_app(app):
    endpoint_name = 'packages_versions'
    service = PackagesVersionsService(endpoint_name, backend=superdesk.get_backend())
    PackagesVersionsResource(endpoint_name, app=app, service=service)

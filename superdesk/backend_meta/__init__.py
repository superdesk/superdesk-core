# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .backend_meta import BackendMetaResource, BackendMetaService
import superdesk


def init_app(app):
    endpoint_name = "backend_meta"
    service = BackendMetaService(endpoint_name, backend=superdesk.get_backend())
    BackendMetaResource(endpoint_name, app=app, service=service)

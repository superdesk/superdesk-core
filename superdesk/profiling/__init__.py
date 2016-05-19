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
from superdesk.profiling.resource import ProfilingResource
from superdesk.profiling.service import ProfilingService, profile


def init_app(app):
    if app.config.get('ENABLE_PROFILING'):
        endpoint_name = 'profiling'
        service = ProfilingService(endpoint_name, backend=None)
        ProfilingResource(endpoint_name, app=app, service=service)

        superdesk.privilege(name='profiling', label='Profiling Service',
                            description='User can read profiling data.')

        profile.enable()

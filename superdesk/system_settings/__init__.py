# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from superdesk.system_settings.resource import SystemSettingsResource
from superdesk.system_settings.service import SystemSettingsService


def init_app(app):
    endpoint_name = 'system_settings'
    service = SystemSettingsService(endpoint_name, backend=superdesk.get_backend())
    SystemSettingsResource(endpoint_name, app=app, service=service)

    superdesk.privilege(name='system_settings', label='System Settings',
                        description='User can manage system settings.')

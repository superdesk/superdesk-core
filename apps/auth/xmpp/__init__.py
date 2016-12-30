# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .auth import XMPPAuthResource
import superdesk
from .auth import XMPPAuthService


def init_app(app):
    endpoint_name = 'auth_xmpp'
    service = XMPPAuthService('auth', backend=superdesk.get_backend())
    XMPPAuthResource(endpoint_name, app=app, service=service)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .auth import XMPPAuthResource, ActivatedResource, XMPPAuthService, ActivatedService
import superdesk


def init_app(app):
    endpoint_name = 'auth_xmpp'
    service = XMPPAuthService('auth', backend=superdesk.get_backend())
    XMPPAuthResource(endpoint_name, app=app, service=service)

    # auth_xmpp_activated endpoint is used to know if XMPP_AUTH_URL is set in config
    # i.e. if secure login is activated
    act_endpoint_name = 'auth_xmpp_activated'
    activated_service = ActivatedService(act_endpoint_name, backend=superdesk.get_backend())
    ActivatedResource(act_endpoint_name, app=app, service=activated_service)

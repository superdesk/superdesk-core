# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Protocol

from .types import HTTPEndpoint, HTTPEndpointGroup


class WSGIApp(Protocol):
    """Protocol for defining functionality from a WSGI application (such as Eve/Flask)

    A class instance that adheres to this protocol is passed into the SuperdeskAsyncApp constructor.
    This way the SuperdeskAsyncApp does not need to know the underlying WSGI application, just that
    it provides certain functionality.
    """

    #: Config for the application
    config: Dict[str, Any]

    def register_endpoint(self, endpoint: HTTPEndpoint):
        ...

    def register_endpoint_group(self, group: HTTPEndpointGroup):
        ...

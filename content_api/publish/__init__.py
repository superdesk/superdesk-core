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

from .resource import PublishResource, MONGO_PREFIX  # noqa
from .service import PublishService


def init_app(app) -> None:
    """Initialize the `publish` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    endpoint_name = "content_api"
    service = PublishService(endpoint_name, backend=superdesk.get_backend())
    PublishResource(endpoint_name, app=app, service=service)

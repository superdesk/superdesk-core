# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .service import ContactsService
from .resource import ContactsResource


def init_app(app) -> None:
    """Initialize the `contacts` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    service = ContactsService(datasource="contacts", backend=superdesk.get_backend())
    ContactsResource(endpoint_name="contacts", app=app, service=service)

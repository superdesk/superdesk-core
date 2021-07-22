# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import superdesk
from .service import SystemMessagesService
from .resource import SystemMessagesResource
from flask_babel import lazy_gettext


logger = logging.getLogger(__name__)


def init_app(app) -> None:
    endpoint_name = "system_messages"
    service = SystemMessagesService(endpoint_name, backend=superdesk.get_backend())
    SystemMessagesResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="system_messages",
        label=lazy_gettext("System Message"),
        description=lazy_gettext("User can manage system messages."),
    )

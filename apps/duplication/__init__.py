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

from .archive_copy import CopyService, CopyResource, init_app as archive_copy_init_app
from .archive_duplication import DuplicateService, DuplicateResource
from .archive_fetch import FetchResource, FetchService
from .archive_move import MoveResource, MoveService
from .archive_translate import TranslateService, TranslateResource
from flask_babel import lazy_gettext


logger = logging.getLogger(__name__)


def init_app(app):
    endpoint_name = "fetch"
    service = FetchService(endpoint_name, backend=superdesk.get_backend())
    FetchResource(endpoint_name, app=app, service=service)

    endpoint_name = "duplicate"
    service = DuplicateService(endpoint_name, backend=superdesk.get_backend())
    DuplicateResource(endpoint_name, app=app, service=service)

    endpoint_name = "translate"
    service = TranslateService(endpoint_name, backend=superdesk.get_backend())
    TranslateResource(endpoint_name, app=app, service=service)

    endpoint_name = "copy"
    service = CopyService(endpoint_name, backend=superdesk.get_backend())
    CopyResource(endpoint_name, app=app, service=service)

    endpoint_name = "move"
    service = MoveService(endpoint_name, backend=superdesk.get_backend())
    MoveResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="fetch", label=lazy_gettext("Fetch Content To a Desk"), description=lazy_gettext("Fetch Content to a Desk")
    )
    superdesk.privilege(
        name="move",
        label=lazy_gettext("Move Content to another desk"),
        description=lazy_gettext("Move Content to another desk"),
    )
    superdesk.privilege(
        name="duplicate",
        label=lazy_gettext("Duplicate Content within a Desk"),
        description=lazy_gettext("Duplicate Content within a Desk"),
    )
    superdesk.privilege(
        name="translate",
        label=lazy_gettext("Translate Content within a Desk"),
        description=lazy_gettext("Translate Content within a Desk"),
    )
    superdesk.privilege(
        name="send_to_personal",
        label=lazy_gettext("Send Content to Personal desk"),
        description=lazy_gettext("Send Content to Personal desk"),
    )

    superdesk.intrinsic_privilege("copy", method=["POST"])

    archive_copy_init_app(app)

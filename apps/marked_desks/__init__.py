# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask_babel import lazy_gettext
import superdesk

from superdesk import get_backend
from apps.marked_desks.resource import MarkedForDesksResource
from apps.marked_desks.service import MarkedForDesksService


def init_app(app) -> None:
    endpoint_name = "marked_for_desks"
    service = MarkedForDesksService(endpoint_name, backend=get_backend())
    MarkedForDesksResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="mark_for_desks",
        label=lazy_gettext("Mark items for desks"),
        description=lazy_gettext("User can mark items for other desks."),
    )
    superdesk.privilege(
        name="mark_for_desks__non_members",
        label=lazy_gettext("Mark items for desks even if the user is not a member of the desk"),
        description=lazy_gettext("User can mark items for other desks even if they are not a member of that desk"),
    )

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.archive_history.service import ArchiveHistoryService, ArchiveHistoryResource
import logging
from superdesk import get_backend

log = logging.getLogger(__name__)


def init_app(app):
    endpoint_name = 'archive_history'

    service = ArchiveHistoryService(endpoint_name, backend=get_backend())
    ArchiveHistoryResource(endpoint_name, app=app, service=service)

    app.on_updated_archive += service.on_item_updated

    app.on_archive_item_updated -= service.on_item_updated
    app.on_archive_item_updated += service.on_item_updated

    app.on_archive_item_deleted -= service.on_item_deleted
    app.on_archive_item_deleted += service.on_item_deleted

    # Store lock information to generate statistics on time spent editing items
    app.on_item_locked -= service.on_item_locked
    app.on_item_locked += service.on_item_locked

    app.on_item_unlocked -= service.on_item_unlocked
    app.on_item_unlocked += service.on_item_unlocked

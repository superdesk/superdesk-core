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
from superdesk.celery_app import celery
from .audit import AuditService, AuditResource
from .commands import PurgeAudit
import logging

log = logging.getLogger(__name__)


def init_app(app) -> None:
    endpoint_name = "audit"

    service = AuditService(endpoint_name, backend=superdesk.get_backend())
    AuditResource(endpoint_name, app=app, service=service)

    app.on_inserted += service.on_generic_inserted
    app.on_updated += service.on_generic_updated
    app.on_deleted_item += service.on_generic_deleted


@celery.task(soft_time_limit=600)
def gc_audit():
    PurgeAudit().run()

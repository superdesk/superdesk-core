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

from superdesk.celery_app import celery
from superdesk import get_backend, privilege
from .resource import LegalArchiveResource, LegalArchiveVersionsResource, LegalPublishQueueResource, \
    LegalArchiveHistoryResource, LEGAL_ARCHIVE_NAME, LEGAL_ARCHIVE_VERSIONS_NAME, \
    LEGAL_ARCHIVE_HISTORY_NAME, LEGAL_PUBLISH_QUEUE_NAME
from .service import LegalArchiveService, LegalArchiveVersionsService, LegalPublishQueueService, \
    LegalArchiveHistoryService
from .commands import ImportLegalPublishQueueCommand, ImportLegalArchiveCommand  # noqa

logger = logging.getLogger(__name__)


def init_app(app):
    if not app.config['LEGAL_ARCHIVE']:
        return

    endpoint_name = LEGAL_ARCHIVE_NAME
    service = LegalArchiveService(endpoint_name, backend=get_backend())
    LegalArchiveResource(endpoint_name, app=app, service=service)

    endpoint_name = LEGAL_ARCHIVE_VERSIONS_NAME
    service = LegalArchiveVersionsService(endpoint_name, backend=get_backend())
    LegalArchiveVersionsResource(endpoint_name, app=app, service=service)

    endpoint_name = LEGAL_ARCHIVE_HISTORY_NAME
    service = LegalArchiveHistoryService(endpoint_name, backend=get_backend())
    LegalArchiveHistoryResource(endpoint_name, app=app, service=service)

    endpoint_name = LEGAL_PUBLISH_QUEUE_NAME
    service = LegalPublishQueueService(endpoint_name, backend=get_backend())
    LegalPublishQueueResource(endpoint_name, app=app, service=service)

    privilege(name=LEGAL_ARCHIVE_NAME, label='Legal Archive', description='Read from legal archive')

    superdesk.command('legal_publish_queue:import', ImportLegalPublishQueueCommand())
    superdesk.command('legal_archive:import', ImportLegalArchiveCommand())


@celery.task(soft_time_limit=300)
def import_legal_publish_queue():
    ImportLegalPublishQueueCommand().run()


@celery.task(soft_time_limit=1800)
def import_legal_archive():
    ImportLegalArchiveCommand().run()

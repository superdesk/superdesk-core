# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


"""Media archive module"""

import logging

import superdesk
from superdesk.celery_app import celery

from .archive import (
    ArchiveResource, ArchiveService,
    ArchiveVersionsResource, ArchiveVersionsService,
    AutoSaveResource, ArchiveSaveService)
from .commands import RemoveExpiredContent
from .ingest import IngestResource, AppIngestService
from .user_content import UserContentResource, UserContentService
from .archive_lock import ArchiveLockResource, ArchiveUnlockResource, ArchiveLockService, ArchiveUnlockService
from .archive_spike import ArchiveUnspikeResource, ArchiveSpikeService, ArchiveSpikeResource, ArchiveUnspikeService
from .related import ArchiveRelatedResource, ArchiveRelatedService
from apps.common.components.utils import register_component
from apps.item_lock.components.item_lock import ItemLock
from apps.common.models.utils import register_model
from apps.item_lock.models.item import ItemModel
from apps.common.models.io.eve_proxy import EveProxy
from .archive_rewrite import ArchiveRewriteResource, ArchiveRewriteService
from .news import NewsResource, NewsService
from flask_babel import _

logger = logging.getLogger(__name__)


def init_app(app):

    endpoint_name = 'ingest'
    service = AppIngestService(endpoint_name, backend=superdesk.get_backend())
    IngestResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_versions'
    service = ArchiveVersionsService(endpoint_name, backend=superdesk.get_backend())
    ArchiveVersionsResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive'
    service = ArchiveService(endpoint_name, backend=superdesk.get_backend())
    ArchiveResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_lock'
    service = ArchiveLockService(endpoint_name, backend=superdesk.get_backend())
    ArchiveLockResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_unlock'
    service = ArchiveUnlockService(endpoint_name, backend=superdesk.get_backend())
    ArchiveUnlockResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_spike'
    service = ArchiveSpikeService(endpoint_name, backend=superdesk.get_backend())
    ArchiveSpikeResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_unspike'
    service = ArchiveUnspikeService(endpoint_name, backend=superdesk.get_backend())
    ArchiveUnspikeResource(endpoint_name, app=app, service=service)

    endpoint_name = 'user_content'
    service = UserContentService(endpoint_name, backend=superdesk.get_backend())
    UserContentResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_rewrite'
    service = ArchiveRewriteService(endpoint_name, backend=superdesk.get_backend())
    ArchiveRewriteResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_autosave'
    service = ArchiveSaveService(endpoint_name, backend=superdesk.get_backend())
    AutoSaveResource(endpoint_name, app=app, service=service)

    endpoint_name = 'archive_related'
    service = ArchiveRelatedService(endpoint_name, backend=superdesk.get_backend())
    ArchiveRelatedResource(endpoint_name, app=app, service=service)

    endpoint_name = 'news'
    service = NewsService(endpoint_name, backend=superdesk.get_backend())
    NewsResource(endpoint_name, app=app, service=service)

    from apps.item_autosave.components.item_autosave import ItemAutosave
    from apps.item_autosave.models.item_autosave import ItemAutosaveModel
    register_component(ItemLock(app))
    register_model(ItemModel(EveProxy(superdesk.get_backend())))
    register_component(ItemAutosave(app))
    register_model(ItemAutosaveModel(EveProxy(superdesk.get_backend())))

    superdesk.privilege(
        name='monitoring_view',
        label=_('Monitoring view'),
        description=_('Access to Monitoring view in left toolbar')
    )
    superdesk.privilege(name='archive', label=_('Create content'), description=_('Create and save content'))
    superdesk.privilege(name='ingest', label=_('Ingest'), description=_('Access to ingest sources management'))
    superdesk.privilege(name='spike', label=_('Spike'), description=_('Spike/delete items'))
    superdesk.privilege(name='spike_read', label=_('Spike view'), description=_('View spiked content'))
    superdesk.privilege(name='unspike', label=_('Unspike'), description=_('Unspike/undelete content'))
    superdesk.privilege(name='metadata_uniquename', label=_('Edit Unique Name'), description=_('Edit unique name'))
    superdesk.privilege(name='hold', label=_('Hold'), description=_('Hold content'))
    superdesk.privilege(name='restore', label=_('Restore'), description=_('Restore content'))
    superdesk.privilege(name='rewrite', label=_('Update'), description=_('Create an update'))
    superdesk.privilege(name='unlock',
                        label=_('Unlock content'),
                        description=_('Unlock locked content by another user'))
    superdesk.privilege(name='mark_for_user',
                        label=_('Mark items for users'),
                        description=_('User can mark or unmark items for other users'))

    superdesk.intrinsic_privilege(ArchiveUnlockResource.endpoint_name, method=['POST'])


@celery.task(soft_time_limit=1800)
def content_expiry():
    RemoveExpiredContent().run()

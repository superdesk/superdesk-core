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
from typing import Any

from flask_babel import lazy_gettext
from superdesk import get_backend
import superdesk

from apps.publish.content import (
    ArchivePublishResource,
    ArchivePublishService,
    KillPublishResource,
    KillPublishService,
    CorrectPublishResource,
    CorrectPublishService,
    ResendResource,
    ResendService,
    TakeDownPublishService,
    TakeDownPublishResource,
    UnpublishResource,
    UnpublishService,
)
from apps.publish.enqueue import EnqueueContent
from apps.publish.published_item import PublishedItemResource, PublishedItemService
from apps.publish.content.published_package_items import PublishedPackageItemsService, PublishedPackageItemsResource


logger = logging.getLogger(__name__)


def init_app(app) -> None:

    endpoint_name = "archive_publish"
    service: Any = ArchivePublishService(endpoint_name, backend=get_backend())
    ArchivePublishResource(endpoint_name, app=app, service=service)

    endpoint_name = "archive_kill"
    service = KillPublishService(endpoint_name, backend=get_backend())
    KillPublishResource(endpoint_name, app=app, service=service)

    endpoint_name = "archive_correct"
    service = CorrectPublishService(endpoint_name, backend=get_backend())
    CorrectPublishResource(endpoint_name, app=app, service=service)

    endpoint_name = "archive_takedown"
    service = TakeDownPublishService(endpoint_name, backend=get_backend())
    TakeDownPublishResource(endpoint_name, app=app, service=service)

    endpoint_name = "published"
    service = PublishedItemService(endpoint_name, backend=get_backend())
    PublishedItemResource(endpoint_name, app=app, service=service)

    endpoint_name = "archive_resend"
    service = ResendService(endpoint_name, backend=get_backend())
    ResendResource(endpoint_name, app=app, service=service)

    endpoint_name = "published_package_items"
    service = PublishedPackageItemsService(endpoint_name, backend=get_backend())
    PublishedPackageItemsResource(endpoint_name, app=app, service=service)

    endpoint_name = "archive_unpublish"
    service = UnpublishService(endpoint_name, backend=get_backend())
    UnpublishResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="subscribers", label=lazy_gettext("Subscribers"), description=lazy_gettext("User can manage subscribers")
    )
    superdesk.privilege(name="publish", label=lazy_gettext("Publish"), description=lazy_gettext("Publish a content"))
    superdesk.privilege(name="kill", label=lazy_gettext("Kill"), description=lazy_gettext("Kill a published content"))
    superdesk.privilege(
        name="correct", label=lazy_gettext("Correction"), description=lazy_gettext("Correction to a published content")
    )
    superdesk.privilege(
        name="publish_queue",
        label=lazy_gettext("Publish Queue"),
        description=lazy_gettext("User can update publish queue"),
    )
    superdesk.privilege(
        name="resend",
        label=lazy_gettext("Resending Stories"),
        description=lazy_gettext("User can resend published stories"),
    )
    superdesk.privilege(
        name="embargo", label=lazy_gettext("Embargo"), description=lazy_gettext("User can set embargo date")
    )
    superdesk.privilege(
        name="takedown", label=lazy_gettext("Take down"), description=lazy_gettext("Take down a published content")
    )
    superdesk.privilege(
        name="unpublish", label=lazy_gettext("Unpublish"), description=lazy_gettext("Unpublish a published content")
    )


def enqueue_content():
    EnqueueContent().run()

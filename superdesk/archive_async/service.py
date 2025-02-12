# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from typing import List, Dict, Any, Optional
from quart import abort
from quart_babel import lazy_gettext as _
from apps.archive.archive_media import ArchiveMediaService
from apps.archive.common import handle_existing_data, on_create_item
from apps.archive.highlights_search_mixin import HighlightsSearchMixin
from apps.auth import get_user
from apps.packages.package_service import PackageService
from apps.stages import StagesService
from superdesk import editor_utils
from superdesk.core.resources.service import AsyncResourceService
from superdesk.errors import SuperdeskApiError
from superdesk.media.crop import CropService
from superdesk.metadata.utils import is_normal_package, is_normal_package_async
from superdesk.resource_fields import ITEMS
from superdesk.types.archive import ArchiveResourceModel


def is_genre(item: ArchiveResourceModel, genre_value: str) -> bool:
    """Item to check specific genre exists or not.

    :param item: item on which the check is performed.
    :param genre_value: genre_value as string
    :return: If exists then true else false
    """
    try:
        return any(genre.qcode.lower() == genre_value.lower() for genre in (item.genre or []))
    except (AttributeError, TypeError):  # from sentry
        return False


def is_item_in_package(item: ArchiveResourceModel) -> bool:
    """Checks if the passed item is a member of a package.

    :param item:
    :return: True if the item belongs to a package
    """
    return bool(item.linked_in_packages is not None and sum(1 for _ in item.linked_in_packages))


class ArchiveService(AsyncResourceService[ArchiveResourceModel], HighlightsSearchMixin):
    packageService = PackageService()
    mediaService = ArchiveMediaService()
    cropService = CropService()

    async def on_fetched(self, docs) -> None:
        """Overriding this to handle existing data in Mongo & Elastic."""
        self.enhance_items(docs[ITEMS])

    async def on_fetched_item(self, doc) -> None:
        self.enhance_items([doc])

    def enhance_items(self, items) -> None:
        for item in items:
            handle_existing_data(item)

    async def on_create(self, docs: list[ArchiveResourceModel]) -> None:
        on_create_item(docs, media_service=self.mediaService)

        for doc in docs:
            if doc.body_footer and is_normal_package_async(doc):
                raise SuperdeskApiError.badRequestError(_("Package doesn't support Public Service Announcements"))

            # FIXME: editor need to be ported to async
            editor_utils.generate_fields(doc)
            await self._test_readonly_stage(doc)

            doc.version_creator = doc.original_creator or None  # avoid ""
            # FIXME

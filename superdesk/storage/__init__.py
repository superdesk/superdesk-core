# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk storage module."""

from typing import Optional
import abc

from eve.io.media import MediaStorage
from eve.io.mongo.media import GridFSMediaStorage, GridFS

from superdesk.core import get_current_app
from .utils import get_mimetype
from .mimetype_mixin import MimetypeMixin


class SuperdeskMediaStorage(MediaStorage, MimetypeMixin):
    @abc.abstractmethod
    def url_for_media(self, media, content_type=None):
        raise NotImplementedError

    @abc.abstractmethod
    def url_for_download(self, media, content_type=None):
        raise NotImplementedError

    @abc.abstractmethod
    def url_for_external(self, media_id: str, resource: Optional[str] = None) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_filename(self, filename):
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_filename_async(self, filename, begin: int = 0, end: int | None = None):
        raise NotImplementedError

    @abc.abstractmethod
    def remove_unreferenced_files(self, existing_files, resource=None):
        raise NotImplementedError

    @abc.abstractmethod
    async def remove_unreferenced_files_async(self, existing_files, resource=None):
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_rendition(self, rendition, resource=None):
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_rendition_async(self, rendition, resource=None):
        raise NotImplementedError

    @abc.abstractmethod
    async def get_async(self, id_or_filename, resource=None, begin: int = 0, end: int | None = None):
        raise NotImplementedError

    @abc.abstractmethod
    async def put_async(self, content, filename=None, content_type=None, resource=None):
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_async(self, id_or_filename, resource=None):
        raise NotImplementedError

    @abc.abstractmethod
    async def exists_async(self, id_or_filename, resource=None):
        raise NotImplementedError


class SimpleMediaStorage(GridFSMediaStorage):
    def fs(self, resource):
        driver = get_current_app().data.mongo

        px = driver.current_mongo_prefix(resource)
        if px not in self._fs:
            self._fs[px] = GridFS(driver.pymongo(prefix=px).db)
        return self._fs[px]


def init_app(app) -> None:
    app.storage = SimpleMediaStorage(app)


from .proxy import ProxyMediaStorage  # noqa
from .desk_media_storage import SuperdeskGridFSMediaStorage  # noqa
from .amazon_media_storage import AmazonMediaStorage  # noqa

from .migrate import cli_media_migrate  # noqa

import superdesk.storage.fix_links  # noqa

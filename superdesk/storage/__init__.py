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

from eve.io.mongo.media import GridFSMediaStorage, GridFS

from .desk_media_storage import SuperdeskGridFSMediaStorage  # NOQA


class SimpleMediaStorage(GridFSMediaStorage):
    def fs(self, resource):
        driver = self.app.data.mongo

        px = driver.current_mongo_prefix(resource)
        if px not in self._fs:
            self._fs[px] = GridFS(driver.pymongo(prefix=px).db)
        return self._fs[px]


def init_app(app):
    app.storage = SimpleMediaStorage(app)

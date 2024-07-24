# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import gridfs
import bson
import bson.errors

from flask_babel import _
from typing import Any, BinaryIO, Dict, Optional, Union
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from superdesk.core.app import get_current_async_app
from superdesk.storage.desk_media_storage import format_id
from .. import SuperdeskMediaStorage


logger = logging.getLogger(__name__)


class GridFSMediaStorageAsync(SuperdeskMediaStorage):
    """
    The GridFSMediaStorageAsync class stores files into GridFS
    using asynchrounous approach.
    """

    def __init__(self, app=None):
        super().__init__(app)
        self._fs = {}

    async def put(
        self,
        content: Union[BinaryIO, bytes, str],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        resource: Optional[str] = None,
        folder: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> Any:
        """Store content in gridfs.

        :param content: binary stream
        :param filename: unique filename
        :param content_type: mime type
        :param metadata: file metadata
        :param resource: type of resource
        :param str folder: Folder that the file will be stored in
        :return str: The ID that was generated for this object
        """

        # try to determine mimetype on the server
        content_type = self._get_mimetype(content, filename, content_type)

        if "_id" in kwargs:
            kwargs["_id"] = format_id(kwargs["_id"])

        if folder:
            if folder[-1] == "/":
                folder = folder[:-1]

            if filename:
                filename = "{}/{}".format(folder, filename)

        if hasattr(content, "read"):
            data = content.read()

            if hasattr(data, "encode"):
                data = data.encode("utf-8")
            if hasattr(content, "seek"):
                content.seek(0)

        try:
            logger.info("Adding file {} to the GridFS".format(filename))

            metadata = metadata or {}
            metadata["contentType"] = content_type

            fs = await self.fs(resource)
            return await fs.upload_from_stream(
                filename,
                content,
                metadata=metadata,
                **kwargs,
            )
        except gridfs.errors.FileExists:
            logger.info("File exists filename=%s id=%s" % (filename, kwargs["_id"]))

    async def fs(self, resource: str = None) -> AsyncIOMotorGridFSBucket:
        resource = resource or "upload"
        mongo = get_current_async_app().mongo

        px = mongo.get_resource_config(resource).prefix
        if px not in self._fs:
            db = mongo.get_db_async(resource)
            self._fs[px] = AsyncIOMotorGridFSBucket(db)

        return self._fs[px]

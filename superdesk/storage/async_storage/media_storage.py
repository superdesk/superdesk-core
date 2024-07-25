# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import logging
import gridfs
from bson import ObjectId

from typing import Any, BinaryIO, Dict, Optional, Union
from motor.motor_asyncio import AsyncIOMotorGridFSBucket, AsyncIOMotorGridOut

from superdesk.core.app import SuperdeskAsyncApp
from superdesk.storage.desk_media_storage import format_id
from .. import SuperdeskMediaStorage


logger = logging.getLogger(__name__)


class GridFSMediaStorageAsync(SuperdeskMediaStorage):
    """
    The GridFSMediaStorageAsync class stores files into GridFS
    using asynchrounous approach.
    """

    _fs: Dict[str, AsyncIOMotorGridFSBucket]
    app: SuperdeskAsyncApp

    def __init__(self, app: SuperdeskAsyncApp = None):
        self.app = app
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
    ) -> ObjectId:
        """Store content in gridfs.

        :param content: binary stream
        :param filename: unique filename
        :param content_type: mime type
        :param metadata: file metadata
        :param resource: type of resource
        :param str folder: Folder that the file will be stored in
        :return str: The ID that was generated for this object
        """

        # try to determine mimetype
        content_type = self._get_mimetype(content, filename, content_type)

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

            if "_id" in kwargs:
                file_id = format_id(kwargs["_id"])
                await fs.upload_from_stream_with_id(file_id, filename, content, metadata=metadata)
                return file_id

            return await fs.upload_from_stream(
                filename,
                content,
                metadata=metadata,
                **kwargs,
            )

        except gridfs.errors.FileExists:
            logger.info("File exists filename=%s id=%s" % (filename, kwargs["_id"]))

    async def get(self, file_id: ObjectId | Any, resource: str = None) -> AsyncIOMotorGridOut | None:
        """
        Retrieve a file from GridFS by its file ID.

        This method fetches a file from GridFS based on the provided file ID. It attempts to parse the
        file's metadata as JSON if possible, logging a warning if any metadata entries are not valid JSON.

        :param file_id: The ID of the file to retrieve. This can be either a bson.ObjectId or any type
                        that can be converted to a bson.ObjectId.
        :param resource: The resource type to use. Defaults to "upload" if not specified.
        :return: The file object retrieved from GridFS, or None if the file does not exist or an error occurs.
        """

        logger.debug("Getting media file with id= %s" % file_id)
        file_id = format_id(file_id)

        try:
            fs = await self.fs(resource)
            media_file = await fs.open_download_stream(file_id)
        except Exception:
            media_file = None

        self._try_parse_metadata(media_file, file_id)

        return media_file

    async def find(
        self, folder: Optional[str] = None, upload_date: Optional[Dict[str, Any]] = None, resource: Optional[str] = None
    ) -> list:
        """
        Search for files in the GridFS.

        Searches for files in the GridFS using a combination of folder name and/or upload date
        comparisons. The upload date comparisons use the same MongoDB BSON comparison operators,
        i.e., `$eq`, `$gt`, `$gte`, `$lt`, `$lte`, and `$ne`, and can be combined together.

        :param folder: Folder name to search within. Only files within this folder will be returned.
                    If not specified, files from all folders will be included.
        :param upload_date: A dictionary specifying the upload date comparison operator and value.
                            For example: {"$lt": datetime.now(timezone.utc)}
        :param resource: The resource type to use. Defaults to "upload".
        :return: A list of files that matched the provided parameters. Each file is represented as
                a dictionary with keys: '_id', 'filename', 'upload_date', and 'size'.
        """

        folder_query = {"filename": {"$regex": "^{}/".format(folder)}} if folder else None
        date_query = {"uploadDate": upload_date} if upload_date else None

        if folder and upload_date:
            query = {"$and": [folder_query, date_query]}
        elif folder:
            query = folder_query
        elif date_query:
            query = date_query
        else:
            query = {}

        files = []
        fs = await self.fs(resource)

        async for file in fs.find(query):
            try:
                files.append(
                    {
                        "_id": file._id,
                        "filename": file.filename,
                        "upload_date": file.uploadDate,
                        "size": file.length,
                        # "_etag": file.md5,
                    }
                )
            except AttributeError as e:
                logging.warning("Failed to get file attributes. {}".format(e))
        return files

    async def exists(self, id_or_query: Union[ObjectId, Any, Dict[str, Any]], resource: str = None) -> bool:
        """
        Check if a file exists in GridFS by its file ID or a query.

        :param id_or_query: The ID of the file to check or a dictionary specifying the search query.
                            This can be either a bson.ObjectId or any type that can be converted to
                            a bson.ObjectId, or a query dictionary.
        :param resource: The resource type to use. Defaults to "upload" if not specified.
        :return: True if the file exists, False otherwise.
        """
        if isinstance(id_or_query, dict):
            query = id_or_query
        else:
            file_id = format_id(id_or_query)
            query = {"_id": file_id}

        fs = await self.fs(resource)
        cursor = fs.find(query).limit(1)
        file_exists = await cursor.to_list(length=1)
        return len(file_exists) > 0

    async def fs(self, resource: str = None) -> AsyncIOMotorGridFSBucket:
        resource = resource or "upload"
        mongo = self.app.mongo

        px = mongo.get_resource_config(resource).prefix
        if px not in self._fs:
            db = mongo.get_db_async(resource)
            self._fs[px] = AsyncIOMotorGridFSBucket(db)

        return self._fs[px]

    def _try_parse_metadata(self, media_file: AsyncIOMotorGridOut, file_id: ObjectId | Any):
        if not (media_file and media_file.metadata):
            return

        for k, v in media_file.metadata.items():
            if isinstance(v, str):
                try:
                    media_file.metadata[k] = json.loads(v)
                except ValueError:
                    logger.info("Non JSON metadata for file: %s with key: %s and value: %s", file_id, k, v)

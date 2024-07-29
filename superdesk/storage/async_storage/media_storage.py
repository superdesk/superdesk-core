# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import json
import gridfs
import logging

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket, AsyncIOMotorGridOut
from typing import Any, BinaryIO, Dict, MutableMapping, Optional, Union, List, cast

from eve.io.media import MediaStorage
from superdesk.core.app import SuperdeskAsyncApp
from superdesk.storage.desk_media_storage import format_id
from superdesk.storage.mimetype_mixin import MimetypeMixin

logger = logging.getLogger(__name__)


class GridFSMediaStorageAsync(MediaStorage, MimetypeMixin):
    """
    The GridFSMediaStorageAsync class stores files into GridFS
    using asynchronous approach.

    .. versionadded:: 3.0
    """
    _fs: Dict[str, AsyncIOMotorGridFSBucket]

    app: SuperdeskAsyncApp

    def __init__(self, app: SuperdeskAsyncApp):
        self.app = app
        self._fs = {}

    async def put(
        self,
        content: Union[BinaryIO, bytes, str],
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        resource: Optional[str] = None,
        folder: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> Union[ObjectId | Any]:
        """Store content in gridfs.

        :param content: binary stream
        :param filename: unique filename
        :param content_type: mime type
        :param metadata: file metadata
        :param resource: type of resource
        :param folder: Folder that the file will be stored in
        :return: The ID that was generated for this object
        """
        # try to determine mimetype
        content_type = self._get_mimetype(content, filename, content_type)

        if folder:
            if folder[-1] == "/":
                folder = folder[:-1]

            if filename:
                filename = f"{folder}/{filename}"

        if hasattr(content, "read"):
            data = content.read()

            if hasattr(data, "encode"):
                data = data.encode("utf-8")
            if hasattr(content, "seek"):
                content.seek(0)

        try:
            logger.info(f"Adding file {filename} to the GridFS")

            metadata = metadata or {}
            metadata["contentType"] = content_type

            fs = await self.fs(resource)

            if "_id" in kwargs:
                file_id = format_id(kwargs["_id"])
                await fs.upload_from_stream_with_id(file_id, filename, content, metadata=metadata)
                return file_id

            return await fs.upload_from_stream(filename, content, metadata=metadata)

        except gridfs.errors.FileExists:
            logger.info(f"File exists filename={filename} id={kwargs.get('_id')}")
            return kwargs["_id"]

    async def get(self, file_id: Union[ObjectId, Any], resource: Optional[str] = None) -> Optional[AsyncIOMotorGridOut]:
        """
        Retrieve a file from GridFS by its file ID.

        This method fetches a file from GridFS based on the provided file ID. It attempts to parse the
        file's metadata as JSON if possible, logging a warning if any metadata entries are not valid JSON.

        :param file_id: The ID of the file to retrieve. This can be either a bson.ObjectId or any type
                        that can be converted to a bson.ObjectId.
        :param resource: The resource to use. Defaults to "upload" if not specified.
        :return: The file object retrieved from GridFS, or None if the file does not exist or an error occurs.
        """
        logger.debug("Getting media file with id= %s" % file_id)
        file_id = format_id(file_id)

        try:
            fs = await self.fs(resource)
            media_file = await fs.open_download_stream(file_id)
        except gridfs.errors.NoFile:
            logger.info(f"No file found with id: {file_id}")
            media_file = None
        except Exception as e:
            logger.error(f"Unexpected exception occurred while getting file with id: {file_id}", exc_info=e)
            media_file = None

        self._try_parse_metadata(media_file, file_id)

        return media_file

    async def find(
        self, folder: Optional[str] = None, upload_date: Optional[Dict[str, Any]] = None, resource: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for files in the GridFS.

        Searches for files in the GridFS using a combination of folder name and/or upload date
        comparisons. The upload date comparisons use the same MongoDB BSON comparison operators,
        i.e., `$eq`, `$gt`, `$gte`, `$lt`, `$lte`, and `$ne`, and can be combined together.

        :param folder: Folder name to search within. Only files within this folder will be returned.
                    If not specified, files from all folders will be included.
        :param upload_date: A dictionary specifying the upload date comparison operator and value.
                            For example: {"$lt": datetime.now(timezone.utc)}
        :param resource: The resource to use. Defaults to "upload".
        :return: A list of files that matched the provided parameters. Each file is represented as
                a dictionary with keys: '_id', 'filename', 'upload_date', and 'size'.
        """
        folder_query = {"filename": {"$regex": f"^{folder}/"}} if folder else None
        date_query = {"uploadDate": upload_date} if upload_date else None
        query: Dict | Dict[str, Dict[str, str]] | None = {}

        if folder and upload_date:
            query = {"$and": [folder_query, date_query]}
        elif folder:
            query = folder_query
        elif date_query:
            query = date_query

        files: List[Any] = []
        fs = await self.fs(resource)

        async for file in fs.find(query):
            # this one below is to please the mypy
            doc: gridfs.GridOut = cast(gridfs.GridOut, file)

            try:
                files.append(
                    {
                        "_id": doc._id,
                        "filename": doc.filename,
                        "upload_date": doc.uploadDate,
                        "size": doc.length,
                        # "_etag": file.md5,
                    }
                )
            except AttributeError as e:
                logging.warning("Failed to get file attributes. {}".format(e))
        return files

    async def exists(self, id_or_query: Union[ObjectId, Any, Dict[str, Any]], resource: Optional[str] = None) -> bool:
        """
        Check if a file exists in GridFS by its file ID or a query.

        :param id_or_query: The ID of the file to check or a dictionary specifying the search query.
                            This can be either a bson.ObjectId or any type that can be converted to
                            a bson.ObjectId, or a query dictionary.
        :param resource: The resource to use. Defaults to "upload" if not specified.
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

    async def delete(self, file_id: Union[ObjectId, Any], resource: Optional[str] = None) -> None:
        """
        Delete a file from GridFS by its file ID.

        :param file_id: The ID of the file to delete. This can be either a bson.ObjectId or any type
                        that can be converted to a bson.ObjectId.
        :param resource: The resource to use. Defaults to "upload" if not specified.

        .. note:: Deletes of non-existent files are considered successful since the end result is the same.
        """
        media_id = ObjectId(file_id) if ObjectId.is_valid(file_id) else file_id
        fs = await self.fs(resource)

        try:
            await fs.delete(media_id)
        except gridfs.errors.NoFile:
            logger.info(f"File with id: {file_id} was not found")

    async def get_by_filename(self, filename: str, resource: Optional[str] = None) -> Optional[AsyncIOMotorGridOut]:
        """
        Retrieve a file from GridFS by its filename.

        :param filename: The filename of the file to retrieve. The filename is expected to include
                        an extension that will be removed to get the file ID.
        :param resource: The resource to use. Defaults to "upload" if not specified.
        :return: The file object retrieved from GridFS, or None if the file does not exist.
        """
        file_id, _ = os.path.splitext(filename)
        return await self.get(file_id, resource)

    async def fs(self, resource: Optional[str] = None) -> AsyncIOMotorGridFSBucket:
        """
        Get the GridFS bucket for the given resource.

        :param resource: The resource to use. Defaults to "upload".
        :return: The GridFS bucket.
        """
        resource = resource or "upload"
        mongo = self.app.mongo

        px = mongo.get_resource_config(resource).prefix
        if px not in self._fs:
            db = mongo.get_db_async(resource)
            self._fs[px] = AsyncIOMotorGridFSBucket(db)

        return self._fs[px]

    def _try_parse_metadata(self, media_file: Optional[AsyncIOMotorGridOut], file_id: Union[ObjectId, Any]) -> None:
        """
        Attempt to parse the metadata of a GridFS file as JSON.

        :param media_file: The file whose metadata to parse.
        :param file_id: The ID of the file.
        """
        if not (media_file and media_file.metadata):
            return

        metadata = cast(MutableMapping[str, Any], media_file.metadata)

        for k, v in media_file.metadata.items():
            if isinstance(v, str):
                try:
                    metadata[k] = json.loads(v)
                except ValueError:
                    logger.info(f"Non JSON metadata for file: {file_id} with key: {k} and value: {v}")

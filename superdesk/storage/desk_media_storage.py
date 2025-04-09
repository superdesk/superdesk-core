# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Optional, cast
from quart_babel import gettext as _
import logging
import json
import mimetypes
from bson import ObjectId
from bson.errors import InvalidId
import gridfs
import os.path
import hashlib

from eve.io.mongo.media import GridFSMediaStorage
from motor.motor_asyncio import AsyncIOMotorGridFSBucket, AsyncIOMotorGridOut

from superdesk.core import get_current_app, get_current_async_app
from superdesk.core.types import SuperdeskFile, SuperdeskAsyncFile
from superdesk.errors import SuperdeskApiError
from . import SuperdeskMediaStorage


logger = logging.getLogger(__name__)


def format_id(media_id) -> ObjectId | str:
    try:
        return ObjectId(media_id)
    except InvalidId:
        return media_id


class GridFSObjectWrapper(SuperdeskFile):
    def __init__(self, media_file: gridfs.GridOut):
        super().__init__()

        self._file = media_file
        blocksize = 65636
        buf = media_file.read(blocksize)
        while len(buf) > 0:
            self.write(buf)
            buf = media_file.read(blocksize)

        self.seek(0)
        self.content_type = media_file.content_type  # type: ignore
        self.length = media_file.length
        self._name = media_file.name
        self.filename = media_file.filename
        self.metadata = media_file.metadata
        self.upload_date = media_file.upload_date
        self.md5 = media_file.md5  # type: ignore
        self._id = media_file._id


class GridFSObjectAsyncWrapper(SuperdeskAsyncFile):
    def __init__(self, media_file: AsyncIOMotorGridOut, begin: int = 0, end: int | None = None):
        # Get the data we know is on the files, even though the types indicate they may be ``None``
        metadata = dict(media_file.metadata or {})
        content_type: str = cast(str, getattr(media_file, "content_type", None) or metadata.get("content_type"))
        md5: str = cast(str, getattr(media_file, "md5", None) or metadata.get("md5"))
        name: str = cast(str, media_file.name)
        filename: str = cast(str, media_file.filename)

        super().__init__(
            buffer=media_file,
            content_type=content_type,
            length=media_file.length,
            name=name,
            filename=filename,
            metadata=metadata,
            upload_date=media_file.upload_date,
            md5=md5,
            media_id=media_file._id,
            begin=begin,
            end=end,
        )


class SuperdeskGridFSMediaStorage(SuperdeskMediaStorage, GridFSMediaStorage):
    def __init__(self, app=None):
        super().__init__(app)
        self._fs_async = {}

    def _process_file_metadata(self, media_file: gridfs.GridOut | AsyncIOMotorGridOut, media_id: ObjectId | str):
        metadata: dict = cast(dict, media_file.metadata or {})

        for k, v in metadata.items():
            if isinstance(v, str):
                try:
                    metadata[k] = json.loads(v)
                except ValueError:
                    logger.info(f"Non JSON metadata for file: {media_id} with key: {k} and value: {v}")

    def get(self, _id, resource=None):
        logger.debug("Getting media file with id= %s" % _id)
        media_id = format_id(_id)
        try:
            media_file = self.fs(resource).get(media_id)
        except Exception:
            media_file = None

        if not media_file:
            return None

        self._process_file_metadata(media_file, media_id)
        return GridFSObjectWrapper(media_file)

    async def get_async(
        self, _id, resource=None, begin: int = 0, end: int | None = None
    ) -> GridFSObjectAsyncWrapper | None:
        logger.debug("Getting media file with id= %s" % _id)
        media_id = format_id(_id)
        try:
            media_file = await self.fs_async(resource).open_download_stream(media_id)
        except Exception:
            media_file = None

        if not media_file:
            return None

        self._process_file_metadata(media_file, media_id)
        return GridFSObjectAsyncWrapper(media_file, begin=begin, end=end)

    def url_for_media(self, media_id, content_type=None):
        """Return url for given media id.

        :param media_id: media id from media_id method
        """
        ext = mimetypes.guess_extension(content_type or "") or ""
        if ext in (".jpe", ".jpeg"):
            ext = ".jpg"
        return get_current_app().upload_url(str(media_id) + ext)

    def url_for_download(self, media_id, content_type=None):
        """Return url for download.

        :param media_id: media id from media_id method
        """
        return get_current_app().download_url(str(media_id))

    def url_for_external(self, media_id: str, resource: Optional[str] = None) -> str:
        """Returns a URL for external use

        Returns a URL for use with the Content/Production API

        :param str media_id: The ID of the asset
        :param str resource: The name of the resource type this Asset is attached to
        :rtype: str
        :return: The URL for external use
        """

        return f"/assets/{media_id}"

    def fetch_rendition(self, rendition, resource=None):
        return self.get(rendition.get("media"), "upload")

    async def fetch_rendition_async(self, rendition, resource=None):
        return await self.get_async(rendition.get("media"), "upload")

    def _get_put_kwargs(
        self, content, filename=None, content_type=None, metadata=None, resource=None, folder=None, **kwargs
    ) -> dict:
        content_type = self._get_mimetype(content, filename, content_type)

        if "_id" in kwargs:
            kwargs["_id"] = format_id(kwargs["_id"])

        if folder:
            if folder[-1] == "/":
                folder = folder[:-1]

            if filename:
                filename = "{}/{}".format(folder, filename)

        if hasattr(content, "read"):
            # Generate the hash in chunks of 8KB,
            # so we're not loading the entire file into memory
            hash_data = hashlib.md5()
            while chunk := content.read(8192):
                hash_data.update(chunk)

            if hasattr(content, "seek"):
                content.seek(0)
        elif isinstance(content, bytes):
            hash_data = hashlib.md5(content)
        elif isinstance(content, str):
            hash_data = hashlib.md5(content.encode("utf-8"))
        else:
            raise SuperdeskApiError.badRequestError(_("Unsupported content type"))

        if metadata is None:
            metadata = {}

        md5 = hash_data.hexdigest()
        metadata.update(
            dict(
                # Store the metadata values as json encoded strings
                md5=f'"{md5}"',
                content_type=f'"{content_type}"',
            )
        )

        return dict(
            content_type=content_type,
            filename=filename,
            metadata=metadata,
            md5=md5,
            **kwargs,
        )

    def put(self, content, filename=None, content_type=None, metadata=None, resource=None, folder=None, **kwargs):
        """Store content in gridfs.

        :param content: binary stream
        :param filename: unique filename
        :param content_type: mime type
        :param metadata: file metadata
        :param resource: type of resource
        :param str folder: Folder that the file will be stored in
        :return str: The ID that was generated for this object
        """

        put_kwargs = self._get_put_kwargs(content, filename, content_type, metadata, resource, folder, **kwargs)

        try:
            logger.info("Adding file {} to the GridFS".format(filename))
            return self.fs(resource).put(content, **put_kwargs)
        except gridfs.errors.FileExists:
            logger.info("File exists filename=%s id=%s" % (filename, kwargs["_id"]))

    async def put_async(
        self, content, filename=None, content_type=None, metadata=None, resource=None, folder=None, **kwargs
    ):
        """Store content in gridfs.

        :param content: binary stream
        :param filename: unique filename
        :param content_type: mime type
        :param metadata: file metadata
        :param resource: type of resource
        :param str folder: Folder that the file will be stored in
        :return str: The ID that was generated for this object
        """

        put_kwargs = self._get_put_kwargs(content, filename, content_type, metadata, resource, folder, **kwargs)

        try:
            logger.info("Adding file {} to the GridFS".format(filename))

            media_id = put_kwargs.pop("_id", None)
            filename = put_kwargs.pop("filename")
            if media_id:
                return await self.fs_async(resource).upload_from_stream_with_id(
                    media_id,
                    filename,
                    content,
                    metadata=put_kwargs,
                )
            else:
                return await self.fs_async(resource).upload_from_stream(
                    filename,
                    content,
                    metadata=put_kwargs,
                )
        except gridfs.errors.FileExists:
            logger.info("File exists filename=%s id=%s" % (filename, kwargs["_id"]))

    def fs(self, resource=None):
        resource = resource or "upload"
        driver = get_current_app().data.mongo
        px = driver.current_mongo_prefix(resource)
        if px not in self._fs:
            self._fs[px] = gridfs.GridFS(driver.pymongo(prefix=px).db)
        return self._fs[px]

    def fs_async(self, resource=None) -> AsyncIOMotorGridFSBucket:
        resource = resource or "upload"
        mongo_async = get_current_async_app().mongo

        try:
            # Attempt to get the driver from async app first
            px = mongo_async.get_resource_config(resource).prefix
            if px not in self._fs_async:
                _, db = mongo_async.get_client_async(resource)
                self._fs_async[px] = AsyncIOMotorGridFSBucket(db)
        except KeyError:
            # Fallback to using the Eve app to get the driver
            driver = get_current_app().data.mongo
            px = driver.current_mongo_prefix(resource)
            if px not in self._fs_async:
                db = get_current_async_app().mongo.get_db_async_from_prefix(px)
                self._fs_async[px] = AsyncIOMotorGridFSBucket(db)

        return self._fs_async[px]

    def remove_unreferenced_files(self, existing_files, resource=None):
        """Get the files from Grid FS and compare against existing files and delete the orphans."""
        current_files = self.fs(resource).find({"_id": {"$nin": list(existing_files)}})
        for file_id in (file._id for file in current_files if str(file._id) not in existing_files):
            print("Removing unused file: ", file_id)
            self.delete(file_id)
        print("Image cleaning completed successfully.")

    async def remove_unreferenced_files_async(self, existing_files, resource=None):
        """Get the files from Grid FS and compare against existing files and delete the orphans."""
        cursor = self.fs_async(resource).find({"_id": {"$nin": list(existing_files)}})
        async for grdfs_file in cursor:
            file_id = str(grdfs_file._id)
            if file_id in existing_files:
                continue
            print("Removing unused file: ", file_id)
            await self.delete_async(file_id)

        print("Image cleaning completed successfully.")

    def _get_find_query(self, folder=None, upload_date=None) -> dict:
        date_query = {"uploadDate": upload_date} if upload_date else None

        if folder:
            folder_query = {"filename": {"$regex": "^{}/".format(folder)}}
            return {"$and": [folder_query, date_query]} if date_query else folder_query

        return date_query or {}

    def find(self, folder=None, upload_date=None, resource=None):
        """Search for files in the GridFS

        Searches for files in the GridFS using a combination of folder name and/or upload date
        comparisons. The upload date comparisons uses the same mongodb BSON comparison operators,
        i.e. `$eq`, `$gt`, `$gte`, `$lt`, `$lte` and `$ne`, and can be combined together.

        :param str folder: Folder name
        :param dict upload_date: Upload date with comparison operator (i.e. $lt, $lte, $gt or $gte)
        :param resource: The resource type to use
        :return list: List of files that matched the provided parameters
        """

        files = []
        for file in self.fs(resource).find(self._get_find_query(folder, upload_date)):
            try:
                files.append(
                    {
                        "_id": file._id,
                        "filename": file.filename,
                        "upload_date": file.upload_date,
                        "size": file.length,
                        "_etag": file.md5,
                    }
                )
            except AttributeError as e:
                logging.warning("Failed to get file attributes. {}".format(e))
        return files

    async def find_async(self, folder=None, upload_date=None, resource=None):
        """Search for files in the GridFS

        Searches for files in the GridFS using a combination of folder name and/or upload date
        comparisons. The upload date comparisons uses the same mongodb BSON comparison operators,
        i.e. `$eq`, `$gt`, `$gte`, `$lt`, `$lte` and `$ne`, and can be combined together.

        :param str folder: Folder name
        :param dict upload_date: Upload date with comparison operator (i.e. $lt, $lte, $gt or $gte)
        :param resource: The resource type to use
        :return list: List of files that matched the provided parameters
        """

        files = []
        async for file in self.fs_async(resource).find(self._get_find_query(folder, upload_date)):
            try:
                files.append(
                    {
                        "_id": file._id,
                        "filename": file.filename,
                        "upload_date": file.upload_date,
                        "size": file.length,
                        "_etag": file.md5,
                    }
                )
            except AttributeError as e:
                logging.warning("Failed to get file attributes. {}".format(e))
        return files

    def exists(self, id_or_filename, resource=None):
        _id = format_id(id_or_filename)
        return self.fs(resource).exists(_id)

    async def exists_async(self, id_or_filename, resource=None):
        if isinstance(id_or_filename, dict):
            query = id_or_filename
        else:
            file_id = format_id(id_or_filename)
            query = {"_id": file_id}

        fs = self.fs_async(resource)
        cursor = fs.find(query).limit(1)
        file_exists = await cursor.to_list(length=1)
        return len(file_exists) > 0

    def get_by_filename(self, filename):
        _id, _ = os.path.splitext(filename)
        return self.get(_id)

    async def get_by_filename_async(self, filename, begin: int = 0, end: int | None = None):
        _id, _ = os.path.splitext(filename)
        return await self.get_async(_id, begin=begin, end=end)

    def delete(self, _id, resource=None):
        return self.fs(resource).delete(format_id(_id))

    async def delete_async(self, _id, resource=None):
        return self.fs_async(resource).delete(format_id(_id))

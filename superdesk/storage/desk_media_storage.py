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
import json
import bson
import gridfs
from eve.io.mongo.media import GridFSMediaStorage
from superdesk.utils import sha


logger = logging.getLogger(__name__)


class SuperdeskGridFSMediaStorage(GridFSMediaStorage):

    def get(self, _id, resource=None):
        logger.debug('Getting media file with id= %s' % _id)
        _id = bson.ObjectId(_id)
        media_file = super().get(_id, resource)
        if media_file and media_file.metadata:
            for k, v in media_file.metadata.items():
                try:
                    if isinstance(v, str):
                        media_file.metadata[k] = json.loads(v)
                except ValueError:
                    logger.exception('Failed to load metadata for file: %s with key: %s and value: %s', _id, k, v)
        return media_file

    def get_redirect_url(self, media_id):
        return None

    def media_id(self, filename, content_type=None, version=True):
        """Get media id for given filename.

        It can be used by async task to first generate id upload file later.

        :param filename: unique file name
        """
        try:
            return bson.ObjectId(str(filename)[:24])  # keep content hash
        except bson.errors.InvalidId:
            return bson.ObjectId(sha(str(filename))[:24])

    def url_for_media(self, media_id, content_type=None):
        """Return url for given media id.

        :param media_id: media id from media_id method
        """
        return self.app.upload_url(str(media_id))

    def url_for_download(self, media_id, content_type=None):
        """Return url for download.

        :param media_id: media id from media_id method
        """
        return self.app.download_url(str(media_id))

    def fetch_rendition(self, rendition):
        return self.get(rendition.get('media'), 'upload')

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
        if '_id' in kwargs:
            kwargs['_id'] = bson.ObjectId(kwargs['_id'])

        if folder:
            if folder[-1] == '/':
                folder = folder[:-1]

            if filename:
                filename = '{}/{}'.format(folder, filename)

        try:
            logger.info('Adding file {} to the GridFS'.format(filename))
            return self.fs(resource).put(content, content_type=content_type,
                                         filename=filename, metadata=metadata, **kwargs)
        except gridfs.errors.FileExists:
            logger.info('File exists filename=%s id=%s' % (filename, kwargs['_id']))

    def fs(self, resource=None):
        resource = resource or 'upload'
        driver = self.app.data.mongo
        px = driver.current_mongo_prefix(resource)
        if px not in self._fs:
            self._fs[px] = gridfs.GridFS(driver.pymongo(prefix=px).db)
        return self._fs[px]

    def remove_unreferenced_files(self, existing_files, resource=None):
        """Get the files from Grid FS and compare against existing files and delete the orphans."""
        current_files = self.fs(resource).find({'_id': {'$nin': list(existing_files)}})
        for file_id in (file._id for file in current_files if str(file._id) not in existing_files):
            print('Removing unused file: ', file_id)
            self.delete(file_id)
        print('Image cleaning completed successfully.')

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
        folder_query = {'filename': {'$regex': '^{}/'.format(folder)}} if folder else None
        date_query = {'uploadDate': upload_date} if upload_date else None

        if folder and upload_date:
            query = {'$and': [folder_query, date_query]}
        elif folder:
            query = folder_query
        elif date_query:
            query = date_query
        else:
            query = {}

        files = []
        for file in self.fs(resource).find(query):
            try:
                files.append({
                    '_id': file._id,
                    'filename': file.filename,
                    'upload_date': file.upload_date,
                    'size': file.length,
                    '_etag': file.md5
                })
            except AttributeError as e:
                logging.warning('Failed to get file attributes. {}'.format(e))
        return files

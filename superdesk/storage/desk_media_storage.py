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
from superdesk.upload import upload_url
from superdesk.utils import sha


logger = logging.getLogger(__name__)


class SuperdeskGridFSMediaStorage(GridFSMediaStorage):

    def get(self, _id, resource):
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
        """Return url for givne media id.

        :param media_id: media id from media_id method
        """
        return upload_url(str(media_id))

    def fetch_rendition(self, rendition):
        return self.get(rendition.get('media'), 'upload')

    def put(self, content, filename=None, content_type=None, metadata=None, resource=None, **kwargs):
        """Store content in gridfs.

        :param content: binary stream
        :param filename: unique filename
        :param content_type: mime type
        :param metadata: file metadata
        :param resource: type of resource
        """
        if '_id' in kwargs:
            kwargs['_id'] = bson.ObjectId(kwargs['_id'])
        try:
            return self.fs(resource).put(content, content_type=content_type,
                                         filename=filename, metadata=metadata, **kwargs)
        except gridfs.errors.FileExists:
            logger.info('File exists filename=%s id=%s' % (filename, kwargs['_id']))

    def fs(self, resource):
        resource = resource or 'upload'
        driver = self.app.data.mongo
        px = driver.current_mongo_prefix(resource)
        if px not in self._fs:
            self._fs[px] = gridfs.GridFS(driver.pymongo(prefix=px).db)
        return self._fs[px]

    def remove_unreferenced_files(self, existing_files):
        """Get the files from Grid FS and compars agains existing files and deletes the orphans."""
        current_files = self.fs('upload').find({'_id': {'$nin': list(existing_files)}})
        for file_id in (file._id for file in current_files if str(file._id) not in existing_files):
            print('Removing unused file: ', file_id)
            self.delete(file_id)
        print('Image cleaning completed successfully.')

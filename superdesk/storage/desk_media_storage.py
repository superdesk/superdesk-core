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


logger = logging.getLogger(__name__)


class SuperdeskGridFSMediaStorage(GridFSMediaStorage):

    def get(self, _id, resource):
        logger.debug('Getting media file with id= %s' % _id)
        try:
            _id = bson.ObjectId(_id)
        except bson.errors.InvalidId:
            pass
        media_file = super().get(_id, resource)
        if media_file and media_file.metadata:
            for k, v in media_file.metadata.items():
                try:
                    if isinstance(v, str):
                        media_file.metadata[k] = json.loads(v)
                except ValueError:
                    logger.exception('Failed to load metadata for file: %s with key: %s and value: %s', _id, k, v)
        return media_file

    def url_for_media(self, media_id):
        return upload_url(str(media_id)[:24])

    def put(self, content, filename, content_type=None, metadata=None, resource=None, **kwargs):
        kwargs.setdefault('_id', bson.ObjectId(str(filename)[:24]))
        try:
            print('id', kwargs['_id'])
            return self.fs(resource).put(content, content_type=content_type,
                                         filename=filename, metadata=metadata, **kwargs)
        except gridfs.errors.FileExists:
            return kwargs['_id']

    def fs(self, resource):
        resource = resource or 'upload'
        driver = self.app.data.mongo
        px = driver.current_mongo_prefix(resource)
        if px not in self._fs:
            self._fs[px] = gridfs.GridFS(driver.pymongo(prefix=px).db)
        return self._fs[px]

    def remove_unreferenced_files(self, existing_files):
        """ Gets the files from Grid FS and compars agains existing files and deletes the orphans """
        current_files = self.fs('upload').find({'_id': {'$nin': list(existing_files)}})
        for file_id in (file._id for file in current_files if str(file._id) not in existing_files):
            print('Removing unused file: ', file_id)
            self.delete(file_id)
        print('Image cleaning completed successfully.')

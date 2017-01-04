# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId
from flask import current_app as app

from superdesk.errors import SuperdeskApiError
from superdesk.media.media_operations import download_file_from_encoded_str, \
    download_file_from_url, process_file_from_stream, decode_metadata
from superdesk.services import BaseService


class AssetsService(BaseService):

    def on_create(self, docs):
        for doc in docs:
            if doc.get('URL') and doc.get('media'):
                message = 'Uploading file by URL and file stream in the same time is not supported.'
                raise SuperdeskApiError.badRequestError(message)

            content = None
            filename = None
            content_type = None
            if doc.get('media'):
                content = doc['media']
                filename, content_type = content.filename, content.mimetype
            elif doc.get('URL'):
                content, filename, content_type = self.download_file(doc)

            self.store_file(doc, content, filename, content_type)
            del doc['media_id']

    def store_file(self, doc, content, filename, content_type):
        # retrieve file name and metadata from file
        file_name, content_type, metadata = process_file_from_stream(content, content_type=content_type)
        try:
            content.seek(0)
            file_id = doc['media_id']
            existing = app.media.get(doc['media_id'], self.datasource)
            if not existing:
                file_id = app.media.put(content, filename=file_name, content_type=content_type,
                                        resource=self.datasource, metadata=metadata, _id=ObjectId(doc['media_id']))
            doc['media'] = file_id
            doc['mime_type'] = content_type
            doc['filemeta'] = decode_metadata(metadata)
        except Exception as io:
            raise SuperdeskApiError.internalError('Saving file failed', exception=io)

    def download_file(self, doc):
        url = doc.get('URL')
        if not url:
            return
        if url.startswith('data'):
            return download_file_from_encoded_str(url)
        else:
            return download_file_from_url(url)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Amazon media storage module."""

from io import BytesIO
from os.path import splitext
from urllib.parse import urlparse
import json
import logging
import time
import unidecode

import boto3
from botocore.client import Config
from eve.io.media import MediaStorage

from superdesk.media.media_operations import download_file_from_url, guess_media_extension
from superdesk.utc import query_datetime
from .mimetype_mixin import MimetypeMixin

logger = logging.getLogger(__name__)
MAX_KEYS = 1000


class AmazonObjectWrapper(BytesIO):

    def __init__(self, s3_object, name, metadata):
        super().__init__()

        s3_body = s3_object['Body']
        blocksize = 65636
        buf = s3_body.read(amt=blocksize)
        while len(buf) > 0:
            self.write(buf)
            buf = s3_body.read(amt=blocksize)

        self.seek(0)
        self.content_type = s3_object['ContentType']
        self.length = int(s3_object['ContentLength'])
        self.name = name
        self.filename = name
        self.metadata = metadata
        self.upload_date = s3_object['LastModified']
        self.md5 = s3_object['ETag'][1:-1]
        self._id = name


class AmazonMediaStorage(MediaStorage, MimetypeMixin):

    def __init__(self, app=None):
        super().__init__(app)
        self.client = boto3.client(
            's3',
            aws_access_key_id=self.app.config['AMAZON_ACCESS_KEY_ID'],
            aws_secret_access_key=self.app.config['AMAZON_SECRET_ACCESS_KEY'],
            region_name=self.app.config.get('AMAZON_REGION'),
            config=Config(signature_version='s3v4'),
            endpoint_url=self.app.config['AMAZON_ENDPOINT_URL'] or None,
        )
        self.user_metadata_header = 'x-amz-meta-'

    def url_for_media(self, media_id, content_type=None):
        return self.app.upload_url(str(media_id))

    def url_for_download(self, media_id, content_type=None):
        return self.app.download_url(str(media_id))

    def _make_s3_safe(self, _id):
        """
        Removes characters from the input _id that may cause issues when using the string as a key in S3 storage.

        See https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingMetadata.html

        :param _id:
        :return:
        """

        def get_translation_table():
            return ''.maketrans({'\\': '',
                                 '{': '',
                                 '^': '',
                                 '}': '',
                                 '%': '',
                                 '`': '',
                                 ']': '',
                                 '>': '',
                                 '[': '',
                                 '~': '',
                                 '<': '',
                                 '#': '',
                                 '|': '',
                                 "'": '',
                                 '"': ''})

        return unidecode.unidecode(str(_id)).translate(get_translation_table())

    def media_id(self, filename, content_type=None, version=True):
        """Get the ``media_id`` path for the given ``filename``.

        if filename doesn't have an extension one is guessed,
        and additional *version* option to have automatic version or not to have,
        or to send a `string` one.
        """
        path = urlparse(filename).path
        file_extension = splitext(path)[1]

        extension = ''
        if not file_extension:
            extension = str(guess_media_extension(content_type)) if content_type else ''

        if version is True:
            # automatic version is set on 15mins granularity.
            mins_granularity = int(int(time.strftime('%M')) / 4) * 4
            version = '%s%s/' % (time.strftime('%Y%m%d%H%m'), mins_granularity)
        elif version is False:
            version = ''
        else:
            version = '%s/' % version.strip('/')

        return '%s%s%s' % (version, self._make_s3_safe(filename), extension)

    def fetch_rendition(self, rendition):
        stream, name, mime = download_file_from_url(rendition.get('href'))
        return stream

    def call(self, method, **kw):
        kw.setdefault('Bucket', self.app.config['AMAZON_CONTAINER_NAME'])
        if 'Key' in kw:
            kw['Key'] = self.get_key(kw['Key'])
        return getattr(self.client, method)(**kw)

    def get_key(self, key):
        subfolder = self.app.config.get('AMAZON_S3_SUBFOLDER', 'false')
        if key and subfolder and subfolder.lower() != 'false':
            key = '%s/%s' % (subfolder.strip('/'), key)
        return key

    def get(self, id_or_filename, resource=None):
        """Open the file given by name or unique id.

        Note that although the returned file is guaranteed to be a File object,
        it might actually be some subclass. Returns None if no file was found.
        """
        id_or_filename = self._make_s3_safe(id_or_filename)
        try:
            obj = self.call('get_object', Key=id_or_filename)
            if obj:
                metadata = self.extract_metadata_from_headers(obj['Metadata'])
                return AmazonObjectWrapper(obj, id_or_filename, metadata)
        except Exception:
            return None
        return None

    def get_all_keys(self):
        """Return the list of all keys from the bucket."""
        all_keys = []
        try:
            for objects in self._get_all_keys_in_batches():
                all_keys.extend(objects)
        except Exception as ex:
            logger.exception(ex)
        return all_keys

    def _get_all_keys_in_batches(self):
        """Return the list of all keys from the bucket in batches."""
        NextMarker = ''
        subfolder = self.app.config.get('AMAZON_S3_SUBFOLDER') or ''
        while True:
            objects = self.call('list_objects', Marker=NextMarker, MaxKeys=MAX_KEYS, Prefix=subfolder)

            if not objects or len(objects.get('Contents', [])) == 0:
                return

            keys = [obj['Key'] for obj in objects.get('Contents', [])]
            NextMarker = keys[-1]
            yield keys

    def extract_metadata_from_headers(self, request_headers):
        headers = {}
        for key, value in request_headers.items():
            if self.user_metadata_header in key:
                new_key = key.split(self.user_metadata_header)[1]
                if(value):
                    try:
                        headers[new_key] = json.loads(value)
                    except Exception as ex:
                        logger.exception(ex)
        return headers

    def put(self, content, filename=None, content_type=None, resource=None, metadata=None, _id=None, version=True,
            folder=None):
        """Save a new file using the storage system, preferably with the name specified.

        If there already exists a file with this name name, the
        storage system may modify the filename as necessary to get a unique
        name. Depending on the storage system, a unique id or the actual name
        of the stored file will be returned. The content type argument is used
        to appropriately identify the file when it is retrieved.

        :param ByteIO content: Data to store in the file object
        :param str filename: Filename used to store the object
        :param str content_type: Content type of the data to be stored
        :param resource: Superdesk resource, i.e. 'upload' or 'download'
        :param metadata: Not currently used with Amazon S3 storage
        :param str _id: ID to be used as the key in the bucket
        :param version: If True the timestamp will be prepended to the key else a string can be used to prepend the key
        :param str folder: The folder to store the object in
        :return str: The ID that was generated for this object
        """
        # XXX: we don't use metadata here as Amazon S3 as a limit of 2048 bytes (keys + values)
        #      and they are anyway stored in MongoDB (and still part of the file). See issue SD-4231
        logger.debug('Going to save file file=%s media=%s ' % (filename, _id))

        # try to determine mimetype on the server
        content_type = self._get_mimetype(content, filename, content_type)

        if not _id:
            _id = self.media_id(filename, content_type=content_type, version=version)

        if folder:
            _id = '%s/%s' % (folder.rstrip('/'), _id)

        found = self._check_exists(_id)
        if found:
            return _id

        kwargs = {}
        acl = self.app.config['AMAZON_OBJECT_ACL']
        if acl:
            # not sure it's really needed here,
            # probably better to turn on/off public-read on the bucket instead
            kwargs['ACL'] = acl

        try:
            self.call(
                'put_object',
                Key=_id,
                Body=content,
                ContentType=content_type,
                **kwargs
            )
            return _id
        except Exception as ex:
            logger.exception(ex)
            raise

    def delete(self, id_or_filename, resource=None):
        id_or_filename = str(id_or_filename)
        del_res = self.call('delete_object', Key=id_or_filename)
        logger.debug('Amazon S3 file deleted %s with status' % id_or_filename, del_res)

    def delete_objects(self, ids):
        """Delete the objects with given list of ids."""
        try:
            delete_parameters = {'Objects': [{'Key': id} for id in ids], 'Quiet': True}
            response = self.call('delete_objects', Delete=delete_parameters)
            if len(response.get('Errors', [])):
                errors = ','.join(['{}:{}'.format(error['Key'], error['Message']) for error in response['Errors']])
                logger.error('Files couldn\'t be deleted: {}'.format(errors))
                return False, errors
            return True, None
        except Exception as ex:
            logger.exception(ex)
            raise

    def exists(self, id_or_filename, resource=None):
        """Test if given name or unique id already exists in storage system."""
        id_or_filename = str(id_or_filename)
        found = self._check_exists(id_or_filename)
        return found

    def _check_exists(self, id_or_filename):
        try:
            self.call('head_object', Key=id_or_filename)
            return True
        except Exception:
            # File not found
            return False

    def remove_unreferenced_files(self, existing_files):
        """Get the files from S3 and compare against existing and delete the orphans."""
        # TODO: Add AMAZON_S3_SUBFOLDER support ref: SDESK-1119
        bucket_files = self.get_all_keys()
        orphan_files = list(set(bucket_files) - existing_files)
        print('There are {} orphan files...'.format(len(orphan_files)))
        for i in range(0, len(orphan_files), MAX_KEYS):
            batch = orphan_files[i:i + MAX_KEYS]
            print('Cleaning %d orphan files...' % len(batch), end='')
            deleted, errors = self.delete_objects(batch)
            if deleted:
                print('done.')
            else:
                print('failed to clean orphans: {}'.format(errors))
        else:
            print('There\'s nothing to clean.')

    def find(self, folder=None, upload_date=None, resource=None):
        """Search for files in the S3 bucket

        Searches for files in the S3 bucket using a combination of folder name and/or upload date
        comparisons. Also uses the `superdesk.utc.query_datetime` method to compare the upload_date provided
        and the upload_date of the file.

        :param str folder: Folder name
        :param dict upload_date: Upload date with comparison operator (i.e. $lt, $lte, $gt or $gte)
        :param resource: The resource type to use
        :return list: List of files that matched the provided parameters
        """

        files = []
        next_marker = ''
        folder = '{}/'.format(folder) if folder else None
        while True:
            result = self.call(
                'list_objects',
                Marker=next_marker,
                MaxKeys=MAX_KEYS,
                Prefix=folder
            )

            if not result or len(result.get('Contents', [])) <= 0:
                break

            objects = result.get('Contents', [])
            for file in objects:
                if upload_date is not None and not query_datetime(file.get('LastModified'), upload_date):
                    continue
                files.append({
                    '_id': file.get('Key'),
                    'filename': file.get('Key'),
                    'upload_date': file.get('LastModified'),
                    'size': file.get('Size'),
                    '_etag': file.get('ETag')
                })

            next_marker = objects[-1]['Key']

        return files

    def getFilename(self, media_id):
        return media_id

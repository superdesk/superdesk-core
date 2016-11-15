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
import json
import logging
from mimetypes import guess_extension
from superdesk.media.media_operations import download_file_from_url
from superdesk.upload import upload_url
import time

import boto3
import bson
from eve.io.media import MediaStorage
from urllib.parse import urlparse
from os.path import splitext


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


def _guess_extension(content_type):
    ext = str(guess_extension(content_type))
    if ext in ['.jpe', '.jpeg']:
        return '.jpg'
    return ext


def url_for_media_default(app, media_id):
    protocol = 'https' if app.config.get('AMAZON_S3_USE_HTTPS', False) else 'http'
    endpoint = 's3-%s.%s' % (app.config.get('AMAZON_REGION'), app.config['AMAZON_SERVER'])
    url = '%s.%s/%s' % (app.config['AMAZON_CONTAINER_NAME'], endpoint, media_id)
    if app.config.get('AMAZON_PROXY_SERVER'):
        url = '%s/%s' % (str(app.config.get('AMAZON_PROXY_SERVER')), url)
    return '%s://%s' % (protocol, url)


def url_for_media_partial(app, media_id):
    protocol = 'https' if app.config.get('AMAZON_S3_USE_HTTPS', False) else 'http'
    url = '%s/%s' % (str(app.config.get('AMAZON_PROXY_SERVER')), media_id)
    return '%s://%s' % (protocol, url)


url_generators = {
    'default': url_for_media_default,
    'partial': url_for_media_partial
}


class AmazonMediaStorage(MediaStorage):

    def __init__(self, app=None):
        super().__init__(app)
        username, api_key = self.read_from_config()
        self.client = boto3.client('s3',
                                   aws_access_key_id=username,
                                   aws_secret_access_key=api_key,
                                   region_name=self.region)
        self.user_metadata_header = 'x-amz-meta-'

    def url_for_media(self, media_id, content_type=None):
        if not self.app.config.get('AMAZON_SERVE_DIRECT_LINKS', False):
            return upload_url(str(media_id))

        if self.app.config.get('AMAZON_PROXY_SERVER'):
            url_generator = url_generators.get(self.app.config.get('AMAZON_URL_GENERATOR', 'default'),
                                               url_for_media_default)
        else:
            url_generator = url_for_media_default
        return url_generator(self.app, media_id)

    def media_id(self, filename, content_type=None, version=True):
        """Get the ``media_id`` path for the given ``filename``.

        if filename doesn't have an extension one is guessed,
        and additional *version* option to have automatic version or not to have,
        or to send a `string` one.

        ``AMAZON_S3_SUBFOLDER`` configuration is used for
        easement deploying multiple instance on the same bucket.
        """
        if not self.app.config.get('AMAZON_SERVE_DIRECT_LINKS', False):
            return str(bson.ObjectId())

        path = urlparse(filename).path
        file_extension = splitext(path)[1]

        extension = ''
        if not file_extension:
            extension = str(_guess_extension(content_type)) if content_type else ''

        subfolder = ''
        env_subfolder = self.app.config.get('AMAZON_S3_SUBFOLDER', 'false')
        if env_subfolder and env_subfolder.lower() != 'false':
            subfolder = '%s/' % env_subfolder.strip('/')

        if version is True:
            # automatic version is set on 15mins granularity.
            mins_granularity = int(int(time.strftime('%M')) / 4) * 4
            version = '%s%s/' % (time.strftime('%Y%m%d%H%m'), mins_granularity)
        elif version is False:
            version = ''
        else:
            version = '%s/' % version.strip('/')

        return '%s%s%s%s' % (subfolder, version, filename, extension)

    def fetch_rendition(self, rendition):
        stream, name, mime = download_file_from_url(rendition.get('href'))
        return stream

    def read_from_config(self):
        self.region = self.app.config.get('AMAZON_REGION', 'us-east-1') or 'us-east-1'
        username = self.app.config['AMAZON_ACCESS_KEY_ID']
        api_key = self.app.config['AMAZON_SECRET_ACCESS_KEY']
        self.container_name = self.app.config['AMAZON_CONTAINER_NAME']
        self.kwargs = {}
        if self.app.config.get('AMAZON_SERVE_DIRECT_LINKS', False):
            self.kwargs['ACL'] = 'public-read'
        return username, api_key

    def get(self, id_or_filename, resource=None):
        """Open the file given by name or unique id.

        Note that although the returned file is guaranteed to be a File object,
        it might actually be some subclass. Returns None if no file was found.
        """
        id_or_filename = str(id_or_filename)
        try:
            obj = self.client.get_object(Key=id_or_filename, Bucket=self.container_name)
            if obj:
                metadata = self.extract_metadata_from_headers(obj['Metadata'])
                return AmazonObjectWrapper(obj, id_or_filename, metadata)
        except:
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
        finally:
            return all_keys

    def _get_all_keys_in_batches(self):
        """Return the list of all keys from the bucket in batches."""
        NextMarker = ''
        while True:
            objects = self.client.list_objects(Bucket=self.container_name, Marker=NextMarker, MaxKeys=MAX_KEYS)

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

    def put(self, content, filename=None, content_type=None, resource=None, metadata=None, _id=None, version=True):
        """Save a new file using the storage system, preferably with the name specified.

        If there already exists a file with this name name, the
        storage system may modify the filename as necessary to get a unique
        name. Depending on the storage system, a unique id or the actual name
        of the stored file will be returned. The content type argument is used
        to appropriately identify the file when it is retrieved.
        """
        # XXX: we don't use metadata here as Amazon S3 as a limit of 2048 bytes (keys + values)
        #      and they are anyway stored in MongoDB (and still part of the file). See issue SD-4231
        logger.debug('Going to save file file=%s media=%s ' % (filename, _id))
        _id = _id or self.media_id(filename, content_type=content_type, version=version)
        found = self._check_exists(_id)
        if found:
            return _id

        try:
            self.client.put_object(Key=_id, Body=content, Bucket=self.container_name,
                                   ContentType=content_type, **self.kwargs)
            return _id
        except Exception as ex:
            logger.exception(ex)
            raise

    def delete(self, id_or_filename, resource=None):
        id_or_filename = str(id_or_filename)
        del_res = self.client.delete_object(Key=id_or_filename, Bucket=self.container_name)
        logger.debug('Amazon S3 file deleted %s with status' % id_or_filename, del_res)

    def delete_objects(self, ids):
        """Delete the objects with given list of ids."""
        try:
            delete_parameters = {'Objects': [{'Key': id} for id in ids], 'Quiet': True}
            response = self.client.delete_objects(Bucket=self.container_name, Delete=delete_parameters)
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
            self.client.head_object(Key=id_or_filename, Bucket=self.container_name)
            return True
        except Exception:
            # File not found
            return False

    def remove_unreferenced_files(self, existing_files):
        """Get the files from S3 and compare against existing and delete the orphans."""
        bucket_files = self.get_all_keys()
        orphan_files = list(set(bucket_files) - existing_files)
        print('There are {} orphan files...'.format(len(orphan_files)))

        if len(orphan_files) > 0:
            print('Cleaning the orphan files...')
            deleted, errors = self.delete_objects(orphan_files)
            if deleted:
                print('Image cleaning completed successfully.')
            else:
                print('Failed to clean orphans: {}'.format(errors))
        else:
            print('There\'s nothing to clean.')

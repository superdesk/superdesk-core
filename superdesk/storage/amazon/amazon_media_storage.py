# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

''' Amazon media storage module'''
import boto3
import json
import bson
import time
import logging
from io import BytesIO
from eve.io.media import MediaStorage
from superdesk.media.media_operations import download_file_from_url
from superdesk.upload import upload_url

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


class AmazonMediaStorage(MediaStorage):

    def __init__(self, app=None):
        super().__init__(app)
        username, api_key = self.read_from_config()
        self.client = boto3.client('s3',
                                   aws_access_key_id=username,
                                   aws_secret_access_key=api_key,
                                   region_name=self.region)
        self.user_metadata_header = 'x-amz-meta-'

    def url_for_media(self, media_id):
        if not self.app.config.get('AMAZON_SERVE_DIRECT_LINKS', False):
            return upload_url(str(media_id))
        protocol = 'https' if self.app.config.get('AMAZON_S3_USE_HTTPS', False) else 'http'
        endpoint = 's3-%s.amazonaws.com' % self.app.config.get('AMAZON_REGION')
        return '%s://%s.%s/%s' % (protocol, self.container_name, endpoint, media_id)

    def media_id(self, filename):
        if not self.app.config.get('AMAZON_SERVE_DIRECT_LINKS', False):
            return str(bson.ObjectId())
        return '%s/%s' % (time.strftime('%Y%m%d'), filename)

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
        """ Opens the file given by name or unique id. Note that although the
        returned file is guaranteed to be a File object, it might actually be
        some subclass. Returns None if no file was found.
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
        """ Returns the list of all keys from the bucket """
        all_keys = []
        try:
            for objects in self._get_all_keys_in_batches():
                all_keys.extend(objects)
        except Exception as ex:
            logger.exception(ex)
        finally:
            return all_keys

    def _get_all_keys_in_batches(self):
        """ Returns the list of all keys from the bucket in batches """
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

    def transform_metadata_to_amazon_format(self, metadata):
        if not metadata:
            return {}
        file_metadata = {}
        for key, value in metadata.items():
            new_key = self.user_metadata_header + key
            file_metadata[new_key] = value
        return file_metadata

    def put(self, content, filename=None, content_type=None, resource=None, metadata=None, _id=None):
        """ Saves a new file using the storage system, preferably with the name
        specified. If there already exists a file with this name name, the
        storage system may modify the filename as necessary to get a unique
        name. Depending on the storage system, a unique id or the actual name
        of the stored file will be returned. The content type argument is used
        to appropriately identify the file when it is retrieved.
        """
        logger.debug('Going to save file file=%s media=%s ' % (filename, _id))
        _id = _id or self.media_id(filename)
        found = self._check_exists(_id)
        if found:
            return _id

        try:
            file_metadata = self.transform_metadata_to_amazon_format(metadata)
            self.client.put_object(Key=_id, Body=content, Bucket=self.container_name,
                                   ContentType=content_type, Metadata=file_metadata, **self.kwargs)
            return _id
        except Exception as ex:
            logger.exception(ex)
            raise

    def delete(self, id_or_filename, resource=None):
        id_or_filename = str(id_or_filename)
        del_res = self.client.delete_object(Key=id_or_filename, Bucket=self.container_name)
        logger.debug('Amazon S3 file deleted %s with status' % id_or_filename, del_res)

    def delete_objects(self, ids):
        """ Deletes the objects with given list of ids"""
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
        """ Returns True if a file referenced by the given name or unique id
        already exists in the storage system, or False if the name is available
        for a new file.
        """
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
        """ Gets the files from S3 and compares against existing and deletes the orphans """
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

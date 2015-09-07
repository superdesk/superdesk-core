# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json

from superdesk import config, app
from superdesk.errors import PublishHTTPPushError
from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import PublishService
from io import BytesIO
from bson import ObjectId
from urllib.parse import urlparse
from http.client import HTTPConnection, HTTPSConnection, InvalidURL
from copy import copy


errors = [PublishHTTPPushError.httpPushError().get_error_description()]


class ItemNotFound(Exception):
    pass

class IdConflict(Exception):
    pass


class HTTPPushService(PublishService):
    """HTTP Publish Service."""
    headers = {"Content-type": "application/json", "Accept": "application/json"}

    def _transmit(self, queue_item, subscriber):
        config = queue_item.get('destination', {}).get('config', {})

        try:
            self._copy_published_media_files(json.loads(queue_item['formatted_item']))

            try:
                self._post(config.get('resource_url'), queue_item['formatted_item'])
            except IdConflict:
                response = self._get(config.get('item_url'), queue_item['item_id'])
                read_item = json.loads(response.read().decode('utf_8'))
                self._patch(config.get('item_url'), queue_item['item_id'], queue_item['formatted_item'], read_item['_etag'])
        except Exception as ex:
            raise PublishHTTPPushError.httpPushError(ex, queue_item.get('destination', {}))

    def _get(self, url, item_id=None):
        '''Retrieve an item from the given resource url
        Raises ItemNotFound if the item identified by item_id (if given) did not exist
        Raises Exception on other errors

        @param url: the resource url
        @param item_id: the item identifier
        @return: HTTPResponse object
        '''
        if item_id:
            url = url.format(item_id)
        request_client = self._request_client(url)
        request_client.request('GET', url)
        response = request_client.getresponse()
        if response.status == 404:
            raise ItemNotFound()
        if response.status != 200:
            raise Exception('Error retrieving url %s: %s' % (url, response.reason))
        return response

    def _post(self, url, formatted_item):
        '''Send a post request to content API
        Raises IdConflict if the item identifier already existed
        Raises Exception on other errors

        @param url: the resource url
        @param formatted_item: string containing the item in the required format
        @return: HTTPResponse object
        '''
        request_client = self._request_client(url)
        request_client.request('POST', url, formatted_item, self.headers)
        response = request_client.getresponse()
        if response.status == 409:
            raise IdConflict()
        if response.status != 201:
            raise Exception('Error pushing item %s' % response.reason)
        return response

    def _headers(self, *custom_headers):
        '''Return headers for an HTTP request

        @param custom_headers: tuples of header-value pairs
        '''
        updated_headers = copy(self.headers)
        updated_headers.update(custom_headers)
        return updated_headers

    def _patch(self, item_url, _id, formatted_item, etag):
        '''Send a patch request to content API to update a given item
        Raises ItemNotFound if the item identified by _id did not exist
        Raises Exception on other errors

        @param item_url: the format of the item url
        @param _id: the item identifier
        @param formatted_item: string containing the item in the required format
        @param etag: the etag of the existing item
        @return: HTTPResponse object
        '''
        url = item_url.format(_id)
        headers = self._headers(self.headers, ('If-Match', etag))
        request_client = self._request_client(url)
        request_client.request('PATCH', url, formatted_item, headers)
        response = request_client.getresponse()
        if response.status == 404:
            raise ItemNotFound()
        if response.status < 200 or response.status >= 300:
            raise Exception('Error pushing item %s' % response.reason)
        return response

    def _request_client(self, url):
        '''Return a HTTP request object that corresponds to the given url
        Raises PublishHTTPPushError on invalid url

        @param url: The URL for which to return the HTTP request client object
        '''
        url_parts = urlparse(url)
        if url_parts.scheme.lower() == 'http':
            return HTTPConnection(url_parts.netloc)
        elif url_parts.scheme.lower() == 'https':
            return HTTPSConnection(url_parts.netloc)
        else:
            raise PublishHTTPPushError.httpPushError(InvalidURL('Invalid HTTP URL %s' % url), config)

    def _copy_published_media_files(self, item):
        '''Copy the media files for the given item to the publish_items endpoint

        @param item: the item object
        '''
        for k, v in item.get('renditions', {}).items():
            if k == 'original_source':
                # if the source is AAP Multimedia then don't copy
                continue

            del v['href']
            if not app.media.exists(v['media'], resource='publish_items'):
                img = app.media.get(v['media'], resource='upload')
                content = BytesIO(img.read())
                content.seek(0)
                _id = app.media.put(content, filename=img.filename, content_type=img.content_type,
                                    metadata=img.metadata, resource='publish_items', _id=ObjectId(v['media']))
                assert str(_id) == v['media']


register_transmitter('HTTPPush', HTTPPushService(), errors)

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
import hmac
import logging
import requests

from superdesk import app
from superdesk.publish import register_transmitter

from superdesk.errors import PublishHTTPPushError, PublishHTTPPushServerError, PublishHTTPPushClientError
from superdesk.publish.publish_queue import PUBLISHED_IN_PACKAGE
from superdesk.publish.publish_service import PublishService
from superdesk.metadata.item import remove_metadata_for_publish

errors = [PublishHTTPPushError.httpPushError().get_error_description()]
logger = logging.getLogger(__name__)


class HTTPPushService(PublishService):
    """HTTP Publish Service.

    The HTTP push service publishes items to the resource service via ``POST`` request.
    For media items it first publishes the media files to the assets service.

    For text items the publish sequence is like this:

    * ``POST`` to resource service the text item

    For media items the publish sequence is like this:

    * Publish media files: for each file from renditions perform the following steps:

        * Verify if the rendition media file exists in the assets service (``GET assets/{media_id}``)
        * If not, upload the rendition media file to the assets service via ``POST`` request

    * Publish the item

    For package items with embedded items config on there is only one publish request to the resource service.

    For package items without embedded items the publish sequence is like this:

    * Publish package items
    * Publish the package item

    **Publishing assets**

    The ``POST`` request to the assets ``URL`` has the ``multipart/form-data`` content type and should
    contain the following fields:

    ``media_id``
        URI string identifying the rendition.

    ``media``
        ``base64`` encoded file content. See `Eve documentation <http://python-eve.org/features.html#file-storage>`_.

    ``mime_type``
        mime type, eg. ``image/jpeg``.

    ``filemeta``
        metadata extracted from binary. Differs based on binary type, eg. could be exif for pictures.

    The response status code is checked - on success it should be ``201 Created``.
    If secret_token is set for destination the x-superdesk-signature header will be added
    for both json and multipart POST requests.
    """

    headers = {"Content-type": "application/json", "Accept": "application/json"}
    hash_header = 'x-superdesk-signature'

    def _transmit(self, queue_item, subscriber):
        """
        @see: PublishService._transmit
        """
        item = json.loads(queue_item['formatted_item'])
        destination = queue_item.get('destination', {})

        self._copy_published_media_files(json.loads(queue_item['formatted_item']), destination)

        if not queue_item.get(PUBLISHED_IN_PACKAGE) or not destination.get('config', {}).get('packaged', False):
            self._push_item(destination, json.dumps(item))

    def _push_item(self, destination, data):
        resource_url = self._get_resource_url(destination)
        headers = self._get_headers(data, destination, self.headers)
        response = requests.post(resource_url, data=data, headers=headers)

        # need to rethrow exception as a superdesk exception for now for notifiers.
        try:
            response.raise_for_status()
        except Exception as ex:
            logger.exception(ex)
            message = 'Error pushing item %s: %s' % (response.status_code, response.text)
            self._raise_publish_error(response.status_code, Exception(message), destination)

    def _copy_published_media_files(self, item, destination):
        """Copy the media files for the given item to the publish_items endpoint

        @param item: the item object
        @type item: dict
        @param assets_url: the url where the media can be uploaded
        @type assets_url: string
        """

        assets_url = self._get_assets_url(destination)

        if not (type(assets_url) == str and assets_url.strip()):
            return

        def parse_media(item):
            media = {}
            renditions = item.get('renditions', {})
            for _, rendition in renditions.items():
                rendition.pop('href', None)
                rendition.setdefault('mimetype', rendition.get('original', {}).get('mimetype', item.get('mimetype')))
                media[rendition['media']] = rendition
            for attachment in item.get('attachments', []):
                media.update({attachment['media']: {
                    'mimetype': attachment['mimetype'],
                    'resource': 'attachments',
                }})
            return media

        media = {}
        media.update(parse_media(item))

        for assoc in item.get('associations', {}).values():
            if assoc is None:
                continue
            media.update(parse_media(assoc))
            for assoc2 in assoc.get('associations', {}).values():
                if assoc2 is None:
                    continue
                media.update(parse_media(assoc2))

        for media_id, rendition in media.items():
            if not self._media_exists(media_id, destination):
                binary = app.media.get(media_id, resource=rendition.get('resource', 'upload'))
                self._transmit_media(binary, destination, exists=False)

    def _transmit_media(self, media, destination, exists=None):
        if exists is None:
            exists = self._media_exists(media._id, destination)
        if exists:
            return
        mimetype = getattr(media, 'content_type', 'image/jpeg')
        data = {'media_id': str(media._id)}
        files = {'media': (str(media._id), media, mimetype)}
        s = requests.Session()
        assets_url = self._get_assets_url(destination)
        request = requests.Request('POST', assets_url)
        prepped = request.prepare()
        prepped.prepare_body(data, files)
        headers = self._get_headers(prepped.body, destination, prepped.headers)
        prepped.prepare_headers(headers)
        response = s.send(prepped)
        if response.status_code not in (200, 201):
            self._raise_publish_error(
                response.status_code,
                Exception('Error pushing media file %s: %s %s' % (
                    str(media._id), response.status_code, response.text
                )),
                destination
            )

    def _media_exists(self, media_id, destination):
        """Returns true if the media with the given id exists at the service identified by assets_url.

        Returns false otherwise. Raises Exception if the error code was not 200 or 404

        @param media_id: the media identifier
        @type media_id: string
        @param assets_url: the url of the assest service
        @type assets_url: string
        @return: bool
        """
        assets_url = self._get_assets_url(destination, media_id)
        response = requests.get(assets_url)
        if response.status_code not in (requests.codes.ok, requests.codes.not_found):  # @UndefinedVariable
            self._raise_publish_error(
                response.status_code,
                Exception('Error querying the assets service %s' % assets_url),
                destination
            )
        return response.status_code == requests.codes.ok  # @UndefinedVariable

    def _get_headers(self, data, destination, current_headers):
        secret_token = self._get_secret_token(destination)
        if not secret_token:
            return current_headers
        data_hash = self._get_data_hash(data, secret_token)
        headers = current_headers.copy()
        headers[self.hash_header] = data_hash
        return headers

    def _get_data_hash(self, data, secret_token):
        if isinstance(data, str):
            encoded_data = bytes(data, 'utf-8')
        else:
            encoded_data = data
        mac = hmac.new(str.encode(secret_token), msg=encoded_data, digestmod='sha1')
        return 'sha1=' + str(mac.hexdigest())

    def _get_secret_token(self, destination):
        return destination.get('config', {}).get('secret_token', None)

    def _get_assets_url(self, destination, media_id=None):
        url = destination.get('config', {}).get('assets_url', None)
        if media_id is not None:
            return '/'.join([url, str(media_id)])
        return url

    def _get_resource_url(self, destination):
        return destination.get('config', {}).get('resource_url')

    def _raise_publish_error(self, status_code, e, destination=None):
        if status_code >= 400 and status_code < 500:
            raise PublishHTTPPushClientError.httpPushError(e, destination)
        elif status_code >= 500 and status_code < 600:
            raise PublishHTTPPushServerError.httpPushError(e, destination)
        else:
            raise PublishHTTPPushError.httpPushError(e, destination)


register_transmitter('http_push', HTTPPushService(), errors)

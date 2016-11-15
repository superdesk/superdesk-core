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
from superdesk import app
from superdesk.publish import register_transmitter

import requests
from superdesk.errors import PublishHTTPPushError, PublishHTTPPushServerError, PublishHTTPPushClientError
from superdesk.publish.publish_queue import PUBLISHED_IN_PACKAGE
from superdesk.publish.publish_service import PublishService


errors = [PublishHTTPPushError.httpPushError().get_error_description()]


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

    The ``POST`` request to the assets ``URL`` has the ``multipart/data-form`` content type and should
    contain the following fields:

    ``media_id``
        URI string identifing the rendition.

    ``media``
        ``base64`` encoded file content. See `Eve documentation <http://python-eve.org/features.html#file-storage>`_.

    ``mime_type``
        mime type, eg. ``image/jpeg``.

    ``filemeta``
        metadata extracted from binary. Differs based on binary type, eg. could be exif for pictures.

    The response status code is checked - on success it should be ``201 Created``.
    """

    headers = {"Content-type": "application/json", "Accept": "application/json"}

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
        response = requests.post(resource_url, data=data, headers=self.headers)

        # need to rethrow exception as a superdesk exception for now for notifiers.
        try:
            response.raise_for_status()
        except Exception:
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

        renditions = item.get('renditions', {})
        for assoc in item.get('associations', {}).values():
            renditions.update(assoc.get('renditions', {}))
        for name, rendition in renditions.items():
            del renditions[name]['href']
            if not self._media_exists(rendition['media'], destination):
                media = app.media.get(rendition['media'], resource='upload')
                files = {'media': (
                    rendition['media'], media, rendition['mimetype']
                )}
                response = requests.post(
                    assets_url, files=files, data={'media_id': rendition['media']}
                )
                if response.status_code != requests.codes.created:  # @UndefinedVariable
                    self._raise_publish_error(
                        response.status_code,
                        Exception('Error pushing item %s media file %s: %s %s' % (
                            item.get("_id", ""), rendition.get('media', ""),
                            response.status_code, response.text
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

        assets_url = self._get_assets_url(destination)
        response = requests.get('%s/%s' % (assets_url, media_id))
        if response.status_code not in (requests.codes.ok, requests.codes.not_found):  # @UndefinedVariable
            self._raise_publish_error(
                response.status_code,
                Exception('Error querying the assets service %s' % assets_url),
                destination
            )
        return response.status_code == requests.codes.ok  # @UndefinedVariable

    def _get_assets_url(self, destination):
        return destination.get('config', {}).get('assets_url', None)

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

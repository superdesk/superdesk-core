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

from eve.utils import config
import requests

from superdesk import app
from superdesk.errors import PublishHTTPPushError
from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import PublishService


errors = [PublishHTTPPushError.httpPushError().get_error_description()]


class HTTPPushService(PublishService):
    """HTTP Publish Service."""
    headers = {"Content-type": "application/json", "Accept": "application/json"}

    def _transmit(self, queue_item, subscriber):
        """
        @see: PublishService._transmit
        """
        item = json.loads(queue_item['formatted_item'])
        item['guid'] = item[config.ID_FIELD]
        del item[config.ID_FIELD]

        assets_url = queue_item.get('destination', {}).get('config', {}).get('assets_url')
        try:
            self._copy_published_media_files(json.loads(queue_item['formatted_item']), assets_url)
        except Exception as e:
            raise PublishHTTPPushError.httpPushError(e, queue_item.get('destination', {}))

        resource_url = queue_item.get('destination', {}).get('config', {}).get('resource_url')
        response = requests.post(resource_url, data=json.dumps(item), headers=self.headers)
        if response.status_code != requests.codes.created:  # @UndefinedVariable
            raise PublishHTTPPushError.httpPushError(Exception('Error pushing item %s' % response.text),
                                                     queue_item.get('destination', {}))

    def _copy_published_media_files(self, item, assets_url):
        """Copy the media files for the given item to the publish_items endpoint

        @param item: the item object
        @type item: dict
        @param assets_url: the url where the media can be uploaded
        @type assets_url: string
        """
        for name, rendition in item.get('renditions', {}).items():
            del item['renditions'][name]['href']
            if not self._media_exists(rendition['media'], assets_url):
                media = app.media.get(rendition['media'], resource='upload')
                files = {'media': (rendition['media'], media, rendition.get('mimetype') or rendition['mime_type'])}
                response = requests.post(assets_url, files=files, data={'media_id': rendition['media']})
                if response.status_code != requests.codes.created:  # @UndefinedVariable
                    raise Exception('Error pushing item %s media file %s' % (item._id, rendition['media']))

    def _media_exists(self, media_id, assets_url):
        """Returns true if the media with the given id exists at the service identified by assets_url.
        Returns false otherwise. Raises Exception if the error code was not 200 or 404

        @param media_id: the media identifier
        @type media_id: string
        @param assets_url: the url of the assest service
        @type assets_url: string
        @return: bool
        """
        response = requests.get('%s/%s' % (assets_url, media_id))
        if response.status_code not in (requests.codes.ok, requests.codes.not_found):  # @UndefinedVariable
            raise Exception('Error querying the assets service %s' % assets_url)
        return response.status_code == requests.codes.ok  # @UndefinedVariable

register_transmitter('http_push', HTTPPushService(), errors)

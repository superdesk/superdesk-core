# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Never
import json
import hmac
import logging
import asyncio

import aiohttp

from superdesk.core import get_current_app, get_config
from superdesk.core.web import AsyncHttpClientSessionMixin
from superdesk.publish import register_transmitter, registered_transmitter_file_providers

from superdesk.errors import PublishHTTPPushError, PublishHTTPPushServerError, PublishHTTPPushClientError
from superdesk.publish import PUBLISHED_IN_PACKAGE
from superdesk.publish.publish_service import PublishService

errors = [PublishHTTPPushError.httpPushError().get_error_description()]
logger = logging.getLogger(__name__)


class HTTPPushService(PublishService, AsyncHttpClientSessionMixin):
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

    NAME = "HTTP Push"

    headers = {"Content-type": "application/json", "Accept": "application/json"}
    hash_header = "x-superdesk-signature"

    async def _transmit(self, queue_item, subscriber):
        """
        @see: PublishService._transmit
        """
        item = json.loads(queue_item["formatted_item"])
        destination = queue_item.get("destination", {})

        await self._copy_published_media_files(json.loads(queue_item["formatted_item"]), destination)

        if not queue_item.get(PUBLISHED_IN_PACKAGE) or not destination.get("config", {}).get("packaged", False):
            await self._push_item(destination, json.dumps(item))

    @classmethod
    def _create_http_session(cls) -> aiohttp.ClientSession:
        # Get the timeouts from the config, and assign to this class before creating the session
        timeouts = get_config(tuple[int, int], "HTTP_PUSH_TIMEOUT", None)
        if timeouts is not None:
            HTTPPushService.http_timeout = aiohttp.ClientTimeout(connect=timeouts[0], sock_read=timeouts[1])
        return super()._create_http_session()

    async def _post(self, destination, url, headers, data) -> aiohttp.ClientResponse:
        try:
            http_client = await self.http_session()
            async with http_client.post(url, headers=headers, data=data) as resp:
                resp.raise_for_status()
                return resp
        except aiohttp.ClientResponseError as error:
            message = f"HTTPPush Response Error {error.status} {error.message}"
            logger.exception(message)
            await self._raise_publish_error(error.status or 400, Exception(message), destination)
        except aiohttp.ClientConnectionError as error:
            message = f"HTTPPush Connection Error {error}"
            logger.exception(message)
            await self._raise_publish_error(504, Exception(message), destination)
        except (asyncio.TimeoutError, TimeoutError):
            message = "HTTPPush Timeout while pushing the item"
            logger.exception(message)
            await self._raise_publish_error(504, Exception(message), destination)
        except asyncio.CancelledError:
            logger.exception("HTTPPush Asyncio Task Cancelled")
            raise

        # This should never happen, but if it does we want to know about it
        message = "HTTPPush unknown error while pushing the item"
        logger.exception(message)
        await self._raise_publish_error(500, Exception(message), destination)

    async def _push_item(self, destination, data):
        resource_url = self._get_resource_url(destination)
        headers = await self._get_headers(data, destination, self.headers)
        await self._post(destination, resource_url, headers, data)

    async def _copy_published_media_files(self, item, destination):
        """Copy the media files for the given item to the publish_items endpoint

        @param item: the item object
        @type item: dict
        @param assets_url: the url where the media can be uploaded
        @type assets_url: string
        """

        assets_url = self._get_assets_url(destination)

        if not (isinstance(assets_url, str) and assets_url.strip()):
            return

        media = {}
        for get_files in registered_transmitter_file_providers:
            media.update(get_files(self.NAME, item))

        app = get_current_app()
        for media_id, rendition in media.items():
            if not await self._media_exists(media_id, destination):
                binary = app.media.get(media_id, resource=rendition.get("resource", "upload"))
                await self._transmit_media(binary, destination, exists=False)

    async def _transmit_media(self, media, destination, exists=None):
        if exists is None:
            exists = await self._media_exists(media._id, destination)
        if exists:
            return
        mimetype = getattr(media, "content_type", "image/jpeg")
        form = aiohttp.FormData()
        form.add_field("media_id", str(media._id))
        form.add_field("media", media, filename=str(media._id), content_type=mimetype)
        assets_url = self._get_assets_url(destination)
        headers = await self._get_headers(form, destination, {})
        response = await self._post(destination, assets_url, headers, form)
        if response.status not in (200, 201):
            await self._raise_publish_error(
                response.status,
                Exception(f"Error pushing media file {media._id}: {response.status} {await response.text()}"),
                destination,
            )

    async def _media_exists(self, media_id, destination) -> bool:
        """Returns true if the media with the given id exists at the service identified by assets_url.

        Returns false otherwise. Raises Exception if the error code was not 200 or 404

        @param media_id: the media identifier
        @type media_id: string
        @param assets_url: the url of the assest service
        @type assets_url: string
        @return: bool
        """
        assets_url = self._get_assets_url(destination, media_id)
        http_client = await self.http_session()
        async with http_client.get(assets_url) as response:
            if response.status not in (200, 404):
                await self._raise_publish_error(
                    response.status, Exception(f"Error querying the assets service {assets_url}"), destination
                )
        return response.status == 200

    async def _get_headers(self, data, destination, current_headers):
        secret_token = self._get_secret_token(destination)
        if not secret_token:
            return current_headers
        data_hash = await self._get_data_hash(data, secret_token)
        headers = current_headers.copy()
        headers[self.hash_header] = data_hash
        return headers

    async def _get_data_hash(self, data, secret_token):
        if isinstance(data, str):
            encoded_data = bytes(data, "utf-8")
        elif isinstance(data, aiohttp.FormData):
            encoded_data = await data().as_bytes()
        else:
            encoded_data = data
        mac = hmac.new(str.encode(secret_token), msg=encoded_data, digestmod="sha1")
        return "sha1=" + str(mac.hexdigest())

    def _get_secret_token(self, destination):
        return destination.get("config", {}).get("secret_token", None)

    def _get_assets_url(self, destination, media_id=None):
        url = destination.get("config", {}).get("assets_url", None)
        if media_id is not None:
            return "/".join([url, str(media_id)])
        return url

    def _get_resource_url(self, destination):
        return destination.get("config", {}).get("resource_url")

    async def _raise_publish_error(self, status_code, e, destination=None) -> Never:
        if status_code >= 400 and status_code < 500:
            raise await PublishHTTPPushClientError.httpPushError(e, destination).send_notifications()
        elif status_code >= 500 and status_code < 600:
            raise await PublishHTTPPushServerError.httpPushError(e, destination).send_notifications()
        else:
            raise await PublishHTTPPushError.httpPushError(e, destination).send_notifications()


register_transmitter("http_push", HTTPPushService(), errors)

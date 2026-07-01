# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import logging
import superdesk
from urllib.parse import urlparse
from io import BytesIO

from superdesk.core import get_current_app
from superdesk.ftp import ftp_connect, FTPClient
from superdesk.publish import register_transmitter, registered_transmitter_file_providers, TransmitterFileEntry
from superdesk.publish.publish_service import get_publish_service, PublishService
from superdesk.errors import PublishFtpError
from superdesk.media.renditions import get_rendition_file_name

errors = [PublishFtpError.ftpError().get_error_description()]

logger = logging.getLogger(__name__)


class FTPPublishService(PublishService):
    """FTP Publish Service.

    It creates files on configured FTP server.

    :param string username: auth username
    :param string password: auth password
    :param path: server path
    :param passive: use passive mode (on by default)
    """

    NAME = "FTP"
    CONFIG = {"passive": True}

    def config_from_url(self, url):
        """Parse given url into ftp config. Used for tests.

        :param url: url in form `ftp://username:password@host:port/dir`
        """
        url_parts = urlparse(url)
        return {
            "username": url_parts.username,
            "password": url_parts.password,
            "host": url_parts.hostname,
            "path": url_parts.path.lstrip("/"),
        }

    async def _get_published_item(self, queue_item):
        try:
            return json.loads(queue_item["formatted_item"])
        except json.JSONDecodeError as ex:
            return await superdesk.get_resource_service("published").find_one_async(
                req=None,
                item_id=queue_item["item_id"],
                _current_version=queue_item["item_version"],
            )

    async def _transmit(self, queue_item, subscriber):
        config = queue_item.get("destination", {}).get("config", {})

        try:
            async with ftp_connect(config) as ftp:
                if config.get("push_associated", False):
                    # Set the working directory for the associated files
                    if "associated_path" in config and config.get("associated_path"):
                        await ftp.change_directory("/" + config.get("associated_path", "").lstrip("/"))

                    item = await self._get_published_item(queue_item)
                    if item:
                        await self._copy_published_media_files(item, ftp)

                    # If the directory was changed to push associated files change it back
                    if "associated_path" in config and config.get("associated_path"):
                        await ftp.change_directory("/" + config.get("path").lstrip("/"))

                filename = get_publish_service().get_filename(queue_item)
                b = BytesIO(queue_item.get("encoded_item", queue_item.get("formatted_item").encode("UTF-8")))
                await ftp.upload_data(filename, b)
        except PublishFtpError:
            raise
        except Exception as ex:
            raise await PublishFtpError.ftpError(ex, queue_item.get("destination")).send_notifications()

    async def _copy_published_media_files(self, item: dict, ftp: FTPClient):
        media: dict[str, TransmitterFileEntry] = {}
        for get_files in registered_transmitter_file_providers:
            media.update(get_files(self.NAME, item))

        # Retrieve the list of files that currently exist in the FTP server
        remote_items = [str(path) for path, _info in await ftp.list()]

        app = get_current_app()
        for media_id, rendition in media.items():
            if not self._media_exists(rendition, remote_items):
                binary = await app.media.get_async(media_id, resource=rendition.get("resource", "upload"))
                await self._transmit_media(binary, rendition, ftp)

    def _media_exists(self, rendition, items):
        for file in items:
            if get_rendition_file_name(rendition) in file:
                return True
        return False

    async def _transmit_media(self, binary: bytes, rendition: TransmitterFileEntry, ftp: FTPClient):  # type: ignore[override]
        await ftp.upload_data(get_rendition_file_name(rendition), binary)


register_transmitter("ftp", FTPPublishService(), errors)

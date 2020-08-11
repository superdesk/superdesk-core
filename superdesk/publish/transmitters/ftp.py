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

from io import BytesIO
from flask import current_app as app

from superdesk.ftp import ftp_connect
from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import get_publish_service, PublishService
from superdesk.errors import PublishFtpError
from superdesk.media.renditions import get_rendition_file_name, get_renditions_spec

errors = [PublishFtpError.ftpError().get_error_description()]

logger = logging.getLogger(__name__)

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


def get_renditions_filter():
    renditions = set(get_renditions_spec(
        without_internal_renditions=True
    ).keys())
    renditions.add('original')
    return renditions


class FTPPublishService(PublishService):
    """FTP Publish Service.

    It creates files on configured FTP server.

    :param string username: auth username
    :param string password: auth password
    :param path: server path
    :param passive: use passive mode (on by default)
    """

    NAME = 'FTP'
    CONFIG = {'passive': True}

    def config_from_url(self, url):
        """Parse given url into ftp config. Used for tests.

        :param url: url in form `ftp://username:password@host:port/dir`
        """
        url_parts = urlparse(url)
        return {
            'username': url_parts.username,
            'password': url_parts.password,
            'host': url_parts.hostname,
            'path': url_parts.path.lstrip('/'),
        }

    def _get_published_item(self, queue_item):
        try:
            return json.loads(queue_item['formatted_item'])
        except json.JSONDecodeError as ex:
            return superdesk.get_resource_service('published').find_one(
                req=None,
                item_id=queue_item['item_id'],
                _current_version=queue_item['item_version'],
            )

    def _transmit(self, queue_item, subscriber):
        config = queue_item.get('destination', {}).get('config', {})

        try:
            with ftp_connect(config) as ftp:

                if config.get('push_associated', False):
                    # Set the working directory for the associated files
                    if 'associated_path' in config and config.get('associated_path'):
                        ftp.cwd('/' + config.get('associated_path', '').lstrip('/'))

                    item = self._get_published_item(queue_item)
                    if item:
                        self._copy_published_media_files(item, ftp)

                    # If the directory was changed to push associated files change it back
                    if 'associated_path' in config and config.get('associated_path'):
                        ftp.cwd('/' + config.get('path').lstrip('/'))

                filename = get_publish_service().get_filename(queue_item)
                b = BytesIO(queue_item.get('encoded_item', queue_item.get('formatted_item').encode('UTF-8')))
                ftp.storbinary('STOR ' + filename, b)
        except PublishFtpError:
            raise
        except Exception as ex:
            raise PublishFtpError.ftpError(ex, config)

    def _copy_published_media_files(self, item, ftp):
        renditions_filter = get_renditions_filter()

        def parse_media(item):
            media = {}
            renditions = item.get('renditions', {})
            for key, rendition in renditions.items():
                if key not in renditions_filter:
                    continue
                if not rendition.get('media'):
                    logger.warn('media missing on rendition %s for item %s', key, item['guid'])
                    continue
                rendition.pop('href', None)
                rendition.setdefault('mimetype', rendition.get('original', {}).get('mimetype', item.get('mimetype')))
                media[rendition['media']] = rendition
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

        # Retrieve the list of files that currently exist in the FTP server
        remote_items = []
        ftp.retrlines('LIST', remote_items.append)

        for media_id, rendition in media.items():
            if not self._media_exists(rendition, remote_items):
                binary = app.media.get(media_id, resource=rendition.get('resource', 'upload'))
                self._transmit_media(binary, rendition, ftp)

    def _media_exists(self, rendition, items):
        for file in items:
            if get_rendition_file_name(rendition) in file:
                return True
        return False

    def _transmit_media(self, binary, rendition, ftp):
        ftp.storbinary('STOR ' + get_rendition_file_name(rendition), binary)


register_transmitter('ftp', FTPPublishService(), errors)

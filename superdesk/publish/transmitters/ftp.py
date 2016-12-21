# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.ftp import ftp_connect
from superdesk.publish import register_transmitter
from io import BytesIO
from superdesk.publish.publish_service import get_publish_service, PublishService
from superdesk.errors import PublishFtpError

errors = [PublishFtpError.ftpError().get_error_description()]

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


class FTPPublishService(PublishService):
    """FTP Publish Service.

    It creates files on configured FTP server.

    :param string username: auth username
    :param string password: auth password
    :param path: server path
    :param passive: use passive mode (on by default)
    """

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

    def _transmit(self, queue_item, subscriber):
        config = queue_item.get('destination', {}).get('config', {})

        try:
            with ftp_connect(config) as ftp:
                filename = get_publish_service().get_filename(queue_item)
                b = BytesIO(queue_item['encoded_item'])
                ftp.storbinary("STOR " + filename, b)
        except PublishFtpError:
            raise
        except Exception as ex:
            raise PublishFtpError.ftpError(ex, config)


register_transmitter('ftp', FTPPublishService(), errors)

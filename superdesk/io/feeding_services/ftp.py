# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
import ftplib
import logging
import tempfile

from datetime import datetime

from superdesk.io.registry import register_feeding_service
from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.utc import utc
from superdesk.etree import etree
from superdesk.io.feeding_services import FeedingService
from superdesk.errors import IngestFtpError
from superdesk.ftp import ftp_connect
from superdesk.io.commands.update_ingest import LAST_UPDATED

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

logger = logging.getLogger(__name__)
DEFAULT_SUCCESS_PATH = "_PROCESSED"
DEFAULT_FAILURE_PATH = "_ERROR"


class FTPFeedingService(FeedingService):
    """
    Feeding Service class which can read article(s) which exist in a file system and accessible using FTP.
    """

    NAME = 'ftp'
    ERRORS = [IngestFtpError.ftpUnknownParserError().get_error_description(),
              IngestFtpError.ftpError().get_error_description()]

    DATE_FORMAT = '%Y%m%d%H%M%S'
    ALLOWED_EXT = {'.json', '.xml'}

    def config_from_url(self, url):
        """
        Parse given url into ftp config.

        :param url: url in form `ftp://username:password@host:port/dir`
        """
        url_parts = urlparse(url)
        return {
            'username': url_parts.username,
            'password': url_parts.password,
            'host': url_parts.hostname,
            'path': url_parts.path.lstrip('/'),
        }

    def _test(self, provider):
        config = provider.get('config', {})
        try:
            with ftp_connect(config) as ftp:
                ftp.mlsd()
        except IngestFtpError:
            raise
        except Exception as ex:
            raise IngestFtpError.ftpError(ex, provider)

    def _move(self, ftp, src, dest):
        """Move distant file

        :param ftp: FTP instance to use
        :type ftp: ftplib.FTP
        :param src: source path of the file to move
        :type src: str
        :param dest: dest path of the file to move
        :type dest: str
        """
        try:
            ftp.rename(src, dest)
        except ftplib.all_errors as e:
            logger.warning("Can't move file from {src} to {dest}: {reason}".format(
                src=src,
                dest=dest,
                reason=e))

    def _create_if_missing(self, ftp, path):
        """Check if a dir exists, and create it else

        :param ftp: FTP instance to use
        :type ftp: ftplib.FTP
        :param src: dir path to check
        :type src: str
        """
        base_path = ftp.pwd()
        try:
            ftp.cwd(path)
        except ftplib.all_errors:
            # path probably doesn't exist
            # catching all_errors is a bit overkill,
            # but ftplib doesn't really have precise error
            # for missing directory
            ftp.mkd(path)
        finally:
            ftp.cwd(base_path)

    def _is_allowed(self, filename):
        """Test if given file is allowed to be ingested."""
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.ALLOWED_EXT

    def _update(self, provider, update):
        config = provider.get('config', {})
        last_updated = provider.get('last_updated')
        crt_last_updated = None
        if config.get('move', False):
            do_move = True
            if not config.get('move_path'):
                logger.debug('missing move_path, default will be used')
            move_dest_path = os.path.join(config.get('path', ''), config.get('move_path') or DEFAULT_SUCCESS_PATH)
            if not config.get('move_path_error'):
                logger.debug('missing move_path_error, default will be used')
            move_dest_path_error = os.path.join(config.get('path', ''),
                                                config.get('move_path_error') or DEFAULT_FAILURE_PATH)
        else:
            do_move = False

        if 'dest_path' not in config:
            config['dest_path'] = tempfile.mkdtemp(prefix='superdesk_ingest_')

        try:
            with ftp_connect(config) as ftp:
                if do_move:
                    try:
                        self._create_if_missing(ftp, move_dest_path)
                        self._create_if_missing(ftp, move_dest_path_error)
                    except ftplib.all_errors as e:
                        logger.warning("Can't create move directory, files will not be moved: {reason}".format(
                            reason=e))
                        do_move = False
                items = []
                for filename, facts in ftp.mlsd():
                    if facts.get('type', '') != 'file':
                        continue
                    try:
                        if not self._is_allowed(filename):
                            logger.info('ignoring file {filename} because of file extension'.format(filename=filename))
                            continue

                        if last_updated:
                            item_last_updated = datetime.strptime(facts['modify'], self.DATE_FORMAT).replace(tzinfo=utc)
                            if item_last_updated < last_updated:
                                continue
                            elif not crt_last_updated or item_last_updated > crt_last_updated:
                                crt_last_updated = item_last_updated

                        local_file_path = os.path.join(config['dest_path'], filename)
                        try:
                            with open(local_file_path, 'xb') as f:
                                try:
                                    ftp.retrbinary('RETR %s' % filename, f.write)
                                except ftplib.all_errors as ex:
                                    os.remove(local_file_path)
                                    raise Exception('Exception retrieving file from FTP server ({filename})'.format(
                                                    filename=filename))
                        except FileExistsError as e:
                            raise Exception('Exception retrieving from FTP server, file already exists ({filename])'
                                            .format(filename=local_file_path))

                        registered_parser = self.get_feed_parser(provider)
                        if isinstance(registered_parser, XMLFeedParser):
                            xml = etree.parse(local_file_path).getroot()
                            parser = self.get_feed_parser(provider, xml)
                            parsed = parser.parse(xml, provider)
                        else:
                            parser = self.get_feed_parser(provider, local_file_path)
                            parsed = parser.parse(local_file_path, provider)

                        if isinstance(parsed, dict):
                            parsed = [parsed]

                        items.append(parsed)
                        if do_move:
                            move_dest_file_path = os.path.join(move_dest_path, filename)
                            self._move(ftp, filename, move_dest_file_path)
                    except Exception as e:
                        logger.error("Error while parsing {filename}: {msg}".format(filename=filename, msg=e))
                        if do_move:
                            move_dest_file_path_error = os.path.join(move_dest_path_error, filename)
                            self._move(ftp, filename, move_dest_file_path_error)
            if crt_last_updated:
                update[LAST_UPDATED] = crt_last_updated
            return items
        except IngestFtpError:
            raise
        except Exception as ex:
            raise IngestFtpError.ftpError(ex, provider)


register_feeding_service(FTPFeedingService.NAME, FTPFeedingService(), FTPFeedingService.ERRORS)

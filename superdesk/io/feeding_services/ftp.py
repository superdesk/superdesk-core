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

from flask import current_app as app
from superdesk.io.registry import register_feeding_service
from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.utc import utc
from superdesk.etree import etree
from superdesk.io.feeding_services import FeedingService
from superdesk.errors import IngestFtpError
from superdesk.ftp import ftp_connect

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

logger = logging.getLogger(__name__)
DEFAULT_SUCCESS_PATH = "_PROCESSED"
DEFAULT_FAILURE_PATH = "_ERROR"


class EmptyFile(Exception):
    """Raised when a file is empty thus ignored"""


class FTPFeedingService(FeedingService):
    """
    Feeding Service class which can read article(s) which exist in a file system and accessible using FTP.
    """

    NAME = 'ftp'

    ERRORS = [IngestFtpError.ftpUnknownParserError().get_error_description(),
              IngestFtpError.ftpError().get_error_description()]

    label = 'FTP feed'

    fields = [
        {
            'id': 'host', 'type': 'text', 'label': 'Host',
            'placeholder': 'FTP Server URL', 'required': True,
            'errors': {5003: 'Server not found.'}
        },
        {
            'id': 'username', 'type': 'text', 'label': 'Username',
            'placeholder': 'Username', 'required': False,
            'errors': {5002: 'Credentials error.'}
        },
        {
            'id': 'password', 'type': 'password', 'label': 'Password',
            'placeholder': 'Password', 'required': False
        },
        {
            'id': 'path', 'type': 'text', 'label': 'Path',
            'placeholder': 'FTP Server Path', 'required': False
        },
        {
            'id': 'dest_path', 'type': 'text', 'label': 'Local Path',
            'placeholder': 'Local Path', 'required': True
        },
        {
            'id': 'passive', 'type': 'boolean', 'label': 'Passive',
            'placeholder': 'Passive', 'required': False, 'default': True
        },
        {
            'id': 'move', 'type': 'boolean', 'label': 'Move items after ingestion',
            'placeholder': 'Move items after ingestion', 'required': False
        },
        {
            'id': 'ftp_move_path', 'type': 'text', 'label': 'Move ingested items to',
            'placeholder': 'FTP Server Path, keep empty to use default path',
            'required': False, 'show_expression': '{move}'
        },
        {
            'id': 'move_path_error', 'type': 'text', 'label': 'Move *NOT* ingested items (i.e. on error) to',
            'placeholder': 'FTP Server Path, keep empty to use default path',
            'required': False, 'show_expression': '{move}'
        }
    ]

    DATE_FORMAT = '%Y%m%d%H%M%S'

    ALLOWED_EXT_DEFAULT = {'.json', '.xml'}

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
            if '500' in str(ex):
                ftp.nlst()
            else:
                raise IngestFtpError.ftpError(ex, provider)

    def _move(self, ftp, src, dest, file_modify, failed):
        """Move distant file

        file won't be moved if it is failed and last modification was made
        recently enough (i.e. before config's INGEST_OLD_CONTENT_MINUTES is
        expired). In other words, if a file fails, it will be tried again until
        INGEST_OLD_CONTENT_MINUTES delay expires.

        :param ftp: FTP instance to use
        :type ftp: ftplib.FTP
        :param src: source path of the file to move
        :type src: str
        :param dest: dest path of the file to move
        :type dest: str
        :param file_modify: date of last file modification
        :type file_modify: datetime
        :param failed: True if something when wrong during ingestion
        :type failed: bool
        """
        if failed and not self.is_old_content(file_modify):
            logger.warning(
                "{src!r} ingestion failed, but we are in the backstop delay, it will be "
                "tried again next time".format(src=src))
            return
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
            if path.startswith('./'):
                ftp.cwd('/')
                ftp.mkd(path)
            elif not path.startswith('/'):
                ftp.mkd('/' + path)
            else:
                ftp.mkd(path)
        finally:
            ftp.cwd(base_path)

    def _create_move_folders(self, config, ftp):
        if not config.get('ftp_move_path'):
            logger.debug('missing move_path, default will be used')
        move_path = os.path.join(config.get('path', ''), config.get('ftp_move_path') or DEFAULT_SUCCESS_PATH)

        if not config.get('move_path_error'):
            logger.debug('missing move_path_error, default will be used')
        move_path_error = os.path.join(config.get('path', ''),
                                       config.get('move_path_error') or DEFAULT_FAILURE_PATH)

        try:
            self._create_if_missing(ftp, move_path)
            self._create_if_missing(ftp, move_path_error)
        except ftplib.all_errors as e:
            logger.error("Can't create move directory: {reason}".format(reason=e))
            raise e

        return move_path, move_path_error

    def _is_allowed(self, filename, allowed_ext):
        """Test if given file is allowed to be ingested."""
        _, ext = os.path.splitext(filename)
        return ext.lower() in allowed_ext

    def _is_empty(self, file_path):
        """Test if given file path is empty, return True if a file is empty
        """
        return not (os.path.isfile(file_path) and os.path.getsize(file_path) > 0)

    def _list_files(self, ftp, provider):
        self._timer.start('ftp_list')
        try:
            return [(filename, facts['modify']) for filename, facts in ftp.mlsd() if facts.get('type') == 'file']
        except Exception as ex:
            if '500' in str(ex):
                file_list = []
                file_name_list = []
                date_list = []
                ftp.dir(file_list.append)
                self.DATE_FORMAT = '%Y %b %d %H:%M:%S'
                for line in file_list:
                    col = line.split()
                    date_string = '{} '.format(datetime.now().year) + ' '.join(col[5:8]) + ':00'
                    date_list.append(date_string)
                    file_name_list.append(col[8])
                return zip(file_name_list, date_list)
            else:
                raise IngestFtpError.ftpError(ex, provider)
        finally:
            self._log_msg("FTP list files. Exec time: {:.4f} secs.".format(self._timer.stop('ftp_list')))

    def _sort_files(self, files):
        self._timer.start('sort_files')
        files = sorted(files, key=lambda x: x[1])
        self._log_msg("Sort {} files. Exec time: {:.4f} secs.".format(len(files), self._timer.stop('sort_files')))
        return files

    def _retrieve_and_parse(self, ftp, config, filename, provider, registered_parser):
        self._timer.start('retrieve_parse')

        if 'dest_path' not in config:
            config['dest_path'] = tempfile.mkdtemp(prefix='superdesk_ingest_')
        local_file_path = os.path.join(config['dest_path'], filename)

        with open(local_file_path, 'wb') as f:
            try:
                ftp.retrbinary('RETR %s' % filename, f.write)
                self._log_msg(
                    "Download finished. Exec time: {:.4f} secs. Size: {} bytes. File: {}.".format(
                        self._timer.split('retrieve_parse'),
                        os.path.getsize(local_file_path),
                        filename
                    )
                )
            except ftplib.all_errors:
                self._log_msg(
                    "Download failed. Exec time: {:.4f} secs. File: {}.".format(
                        self._timer.stop('retrieve_parse'),
                        filename
                    )
                )
                os.remove(local_file_path)
                raise Exception('Exception retrieving file from FTP server ({filename})'.format(
                                filename=filename))

        if self._is_empty(local_file_path):
            logger.info('ignoring empty file {filename}'.format(filename=filename))
            raise EmptyFile(local_file_path)

        if isinstance(registered_parser, XMLFeedParser):
            xml = etree.parse(local_file_path).getroot()
            parser = self.get_feed_parser(provider, xml)
            parsed = parser.parse(xml, provider)
        else:
            parser = self.get_feed_parser(provider, local_file_path)
            parsed = parser.parse(local_file_path, provider)

        self._log_msg(
            "Parsing finished. Exec time: {:.4f} secs. File: {}.".format(
                self._timer.stop('retrieve_parse'),
                filename
            )
        )

        return [parsed] if isinstance(parsed, dict) else parsed

    def _update(self, provider, update):
        config = provider.get('config', {})
        do_move = config.get('move', False)
        last_processed_file_modify = provider.get('private', {}).get('last_processed_file_modify')
        limit = app.config.get('FTP_INGEST_FILES_LIST_LIMIT', 100)
        registered_parser = self.get_feed_parser(provider)
        allowed_ext = getattr(registered_parser, 'ALLOWED_EXT', self.ALLOWED_EXT_DEFAULT)

        try:
            self._timer.start('ftp_connect')
            with ftp_connect(config) as ftp:
                self._log_msg("Connected to FTP server. Exec time: {:.4f} secs.".format(
                    self._timer.stop('ftp_connect')
                ))
                files_to_process = []
                files = self._sort_files(self._list_files(ftp, provider))

                if do_move:
                    move_path, move_path_error = self._create_move_folders(config, ftp)

                self._timer.start('files_to_process')

                for filename, modify in files:
                    # filter by extension
                    if not self._is_allowed(filename, allowed_ext):
                        logger.info('ignoring file {filename} because of file extension'.format(filename=filename))
                        continue

                    # filter by modify datetime
                    file_modify = datetime.strptime(modify, self.DATE_FORMAT).replace(tzinfo=utc)
                    if last_processed_file_modify:
                        # ignore limit and add files for processing
                        if last_processed_file_modify == file_modify:
                            files_to_process.append((filename, file_modify))
                        elif last_processed_file_modify < file_modify:
                            # even if we have reached a limit, we must add at least one file to increment
                            # a `last_processed_file_modify` in provider
                            files_to_process.append((filename, file_modify))
                            # limit amount of files to process per ingest update
                            if len(files_to_process) >= limit:
                                break
                    else:
                        # limit amount of files to process per ingest update
                        if len(files_to_process) >= limit:
                            break
                        # add files for processing
                        files_to_process.append((filename, file_modify))

                self._log_msg(
                    "Got {} file for processing. Exec time: {:.4f} secs.".format(
                        len(files_to_process), self._timer.stop('files_to_process')
                    )
                )

                # process files
                self._timer.start('start_processing')
                for filename, file_modify in files_to_process:
                    try:
                        update['private'] = {'last_processed_file_modify': file_modify}
                        failed = yield self._retrieve_and_parse(ftp, config, filename, provider, registered_parser)

                        if do_move:
                            move_dest_file_path = os.path.join(move_path if not failed else move_path_error, filename)
                            self._move(
                                ftp, filename, move_dest_file_path, file_modify,
                                failed=failed)
                    except EmptyFile:
                        continue
                    except Exception as e:
                        logger.error("Error while parsing {filename}: {msg}".format(filename=filename, msg=e))

                        if do_move:
                            move_dest_file_path_error = os.path.join(move_path_error, filename)
                            self._move(
                                ftp, filename, move_dest_file_path_error, file_modify,
                                failed=True)

                self._log_msg(
                    "Processing finished. Exec time: {:.4f} secs.".format(self._timer.stop('start_processing'))
                )

        except IngestFtpError:
            raise
        except Exception as ex:
            raise IngestFtpError.ftpError(ex, provider)


register_feeding_service(FTPFeedingService)

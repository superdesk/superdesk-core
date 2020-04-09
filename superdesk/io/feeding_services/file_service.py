# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import os
import shutil
from datetime import datetime
from lxml import etree
from flask import current_app as app
from superdesk.errors import IngestFileError, ParserError, ProviderError
from superdesk.io.registry import register_feeding_service
from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.io.feeding_services import FeedingService, OLD_CONTENT_MINUTES
from superdesk.notification import push_notification
from superdesk.utc import utc
from superdesk.utils import get_sorted_files, FileSortAttributes

logger = logging.getLogger(__name__)


class FileFeedingService(FeedingService):
    """
    Feeding Service class which can read the configured local file system for article(s).
    """

    NAME = 'file'

    ERRORS = [
        ParserError.IPTC7901ParserError().get_error_description(),
        ParserError.nitfParserError().get_error_description(),
        ParserError.newsmlOneParserError().get_error_description(),
        ProviderError.ingestError().get_error_description(),
        ParserError.parseFileError().get_error_description()
    ]

    label = 'File feed'

    fields = [
        {
            'id': 'path', 'type': 'text', 'label': 'Server Folder',
            'placeholder': 'path to folder', 'required': True,
            'errors': {3003: 'Path not found on server.', 3004: 'Path should be directory.'}
        }
    ]

    def _test(self, provider):
        path = provider.get('config', {}).get('path', None)
        if not os.path.exists(path):
            raise IngestFileError.notExistsError()
        if not os.path.isdir(path):
            raise IngestFileError.isNotDirError()

    def _update(self, provider, update):
        # check if deprecated FILE_INGEST_OLD_CONTENT_MINUTES setting is still used
        if "FILE_INGEST_OLD_CONTENT_MINUTES" in app.config:
            deprecated_cont_min = app.config["FILE_INGEST_OLD_CONTENT_MINUTES"]
            cont_min = app.config[OLD_CONTENT_MINUTES]
            if deprecated_cont_min != cont_min:
                logger.warning(
                    "'FILE_INGEST_OLD_CONTENT_MINUTES' is deprecated, please update settings.py to use {new_name!r}"
                    .format(new_name=OLD_CONTENT_MINUTES))
                app.config[OLD_CONTENT_MINUTES] = deprecated_cont_min

        self.provider = provider
        self.path = provider.get('config', {}).get('path', None)

        if not self.path:
            logger.warn('File Feeding Service {} is configured without path. Please check the configuration'
                        .format(provider['name']))
            return []

        registered_parser = self.get_feed_parser(provider)
        for filename in get_sorted_files(self.path, sort_by=FileSortAttributes.created):
            try:
                last_updated = None
                file_path = os.path.join(self.path, filename)
                if os.path.isfile(file_path):
                    last_updated = self.get_last_updated(file_path)

                    if self.is_latest_content(last_updated, provider.get('last_updated')):
                        if isinstance(registered_parser, XMLFeedParser):
                            with open(file_path, 'rb') as f:
                                xml = etree.parse(f)
                                parser = self.get_feed_parser(provider, xml.getroot())
                                item = parser.parse(xml.getroot(), provider)
                        else:
                            parser = self.get_feed_parser(provider, file_path)
                            item = parser.parse(file_path, provider)

                        self.after_extracting(item, provider)

                        if isinstance(item, list):
                            failed = yield item
                        else:
                            failed = yield [item]

                        self.move_file(self.path, filename, provider=provider, success=not failed)
                    else:
                        self.move_file(self.path, filename, provider=provider, success=False)
            except Exception as ex:
                if last_updated and self.is_old_content(last_updated):
                    self.move_file(self.path, filename, provider=provider, success=False)
                raise ParserError.parseFileError('{}-{}'.format(provider['name'], self.NAME), filename, ex, provider)

        push_notification('ingest:update')

    def after_extracting(self, article, provider):
        """Sub-classes should override this method if something needs to be done to the given article.

        For example, if the article comes from DPA provider the system needs to derive dateline
        from the properties in the article.

        Invoked after parser parses the article received from the provider.

        :param article: dict having properties that can be saved into ingest collection
        :type article: dict
        :param provider: dict - Ingest provider details to which the current directory has been configured
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        """
        pass

    def move_file(self, file_path, filename, provider, success=True):
        """Move the files from the current directory to the _Processed if successful, else _Error if unsuccessful.

        Creates _Processed and _Error directories within current directory if they don't exist.

        :param file_path: str - current directory location
        :param filename: str - file name in the current directory to move
        :param provider: dict - Ingest provider details to which the current directory has been configured
        :param success: bool - default value is True. When True moves to _Processed directory else _Error directory.
        :raises IngestFileError.folderCreateError() if creation of _Processed or _Error directories fails
        :raises IngestFileError.fileMoveError() if failed to move the file pointed by filename
        """

        try:
            if not os.path.exists(os.path.join(file_path, "_PROCESSED/")):
                os.makedirs(os.path.join(file_path, "_PROCESSED/"))
            if not os.path.exists(os.path.join(file_path, "_ERROR/")):
                os.makedirs(os.path.join(file_path, "_ERROR/"))
        except Exception as ex:
            raise IngestFileError.folderCreateError(ex, provider)

        try:
            if success:
                shutil.copy2(os.path.join(file_path, filename), os.path.join(file_path, "_PROCESSED/"))
            else:
                shutil.copy2(os.path.join(file_path, filename), os.path.join(file_path, "_ERROR/"))
        except Exception as ex:
            raise IngestFileError.fileMoveError(ex, provider)
        finally:
            os.remove(os.path.join(file_path, filename))

    def get_last_updated(self, file_path):
        """Get last updated time for file.

        Using both mtime and ctime timestamps not to miss
        old files being copied around and recent files after
        changes done in place.
        """
        stat = os.lstat(file_path)
        timestamp = max(stat.st_mtime, stat.st_ctime)
        return datetime.fromtimestamp(timestamp, tz=utc)


register_feeding_service(FileFeedingService)

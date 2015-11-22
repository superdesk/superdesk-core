# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license*.


import logging
import os
from datetime import datetime

from superdesk.errors import ParserError, ProviderError
from superdesk.io.feeding_services.file_service import FileFeedingService
from superdesk.utc import utc
from superdesk.utils import get_sorted_files, FileSortAttributes

logger = logging.getLogger(__name__)


class TeletypeFeedingService(FileFeedingService):

    NAME = 'teletype'

    ERRORS = [ParserError.ZCZCParserError().get_error_description(),
              ProviderError.ingestError().get_error_description(),
              ParserError.parseFileError().get_error_description()]

    def _update(self, provider):
        self.provider = provider
        self.path = provider.get('config', {}).get('path', None)

        if not self.path:
            logger.info('No path')
            return []

        for filename in get_sorted_files(self.path, sort_by=FileSortAttributes.created):
            try:
                filepath = os.path.join(self.path, filename)
                if os.path.isfile(filepath):
                    stat = os.lstat(filepath)
                    last_updated = datetime.fromtimestamp(stat.st_mtime, tz=utc)
                    if self.is_latest_content(last_updated, provider.get('last_updated')):
                        parser = self.get_feed_parser(provider, filepath)
                        item = parser.parse_file(filepath, provider)
                        self.move_file(self.path, filename, provider=provider, success=True)

                        yield [item]
                    else:
                        self.move_file(self.path, filename, provider=provider, success=True)
            except Exception as ex:
                self.move_file(self.path, filename, provider=provider, success=False)
                raise ParserError.parseFileError('Teletype', filename, ex, provider)

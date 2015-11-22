# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feeding_services import FeedingService
from datetime import timedelta
import os
import shutil
from superdesk.utc import utcnow
from superdesk.errors import IngestFileError


class FileFeedingService(FeedingService):
    """
    Base class for Ingest Services which get items from a file system
    """

    def _update(self, provider):
        raise NotImplementedError()

    def move_file(self, file_path, filename, provider, success=True):
        """
        Move the files from the current directory to the _Processed if successful, else _Error if unsuccessful.
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

    def is_latest_content(self, last_updated, provider_last_updated=None):
        """
        Parse file only if it's not older than provider last update -10m
        """

        if not provider_last_updated:
            provider_last_updated = utcnow() - timedelta(days=7)

        return provider_last_updated - timedelta(minutes=10) < last_updated

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016, 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import superdesk
from datetime import timedelta

from flask import current_app as app
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


class RemoveExportedFiles(superdesk.Command):
    """Remove files from storage that were used for exporting items

    Example:
    ::

        $ python manage.py storage:remove_exported
        $ python manage.py storage:remove_exported --expire-hours=12

    """

    log_msg = ""
    expire_hours = 24

    option_list = [superdesk.Option("--expire-hours", "-e", dest="expire_hours", required=False, type=int)]

    def run(self, expire_hours=None):
        if expire_hours:
            self.expire_hours = expire_hours
        elif "TEMP_FILE_EXPIRY_HOURS" in app.config:
            self.expire_hours = app.config["TEMP_FILE_EXPIRY_HOURS"]

        expire_at = utcnow() - timedelta(hours=self.expire_hours)
        self.log_msg = "Expiry Time: {}.".format(expire_at)
        logger.info("{} Starting to remove exported files from storage".format(self.log_msg))

        lock_name = get_lock_id("storage", "remove_exported")
        if not lock(lock_name, expire=300):
            logger.info("Remove exported files from storage task is already running")
            return

        try:
            logger.info("{} Removing expired temporary media files".format(self.log_msg))
            self._remove_exported_files(expire_at)
        finally:
            unlock(lock_name)

        logger.info("{} Completed removing exported files from storage".format(self.log_msg))

    def _remove_exported_files(self, expire_at):
        logger.info("{} Beginning to remove exported files from storage".format(self.log_msg))
        for file_id in self._get_file_ids(expire_at):
            app.media.delete(file_id)

    def _get_file_ids(self, expire_at):
        files = app.media.find(folder="temp", upload_date={"$lte": expire_at})
        return [file["_id"] for file in files]


superdesk.command("storage:remove_exported", RemoveExportedFiles())

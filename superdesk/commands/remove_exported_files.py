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
from datetime import timedelta

import click

from superdesk.core import get_current_app
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock
from superdesk.utc import utcnow

from .async_cli import cli

logger = logging.getLogger(__name__)


@cli.command("storage:remove_exported")
@click.option("--expire-hours", "-e", "expire_hours", required=False, type=int)
def cli_storage_remove_exported(expire_hours: int | None = None):
    """Remove files from storage that were used for exporting items

    Example:
    ::

        $ python manage.py storage:remove_exported
        $ python manage.py storage:remove_exported --expire-hours=12

    """

    RemoveExportedFiles().run(expire_hours)


class RemoveExportedFiles:
    log_msg = ""
    expire_hours = 24

    def run(self, expire_hours=None):
        app = get_current_app()
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
        app = get_current_app()
        for file_id in self._get_file_ids(expire_at):
            app.media.delete(file_id)

    def _get_file_ids(self, expire_at):
        files = get_current_app().media.find(folder="temp", upload_date={"$lte": expire_at})
        return [file["_id"] for file in files]

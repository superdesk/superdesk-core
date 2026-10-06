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
from datetime import datetime

import superdesk
from eve.utils import config

from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, UpdateConflictError
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE
from superdesk.utc import get_expiry_date, utcnow
from .archive import SOURCE as ARCHIVE
from .common import get_item_expiry

logger = logging.getLogger(__name__)


class SetExpiry(superdesk.Command):
    """Reset expiry on active unpublished items on a desk, without creating versions.

    The desk is selected by its exact name. Expiry is calculated from the command's
    start time, or each item's last update with ``--from-updated``.
    With no ``--days``, use stage, desk and global expiry settings in
    that order. Spiked, scheduled and published content (including corrections)
    is excluded. Both MongoDB and Elasticsearch are updated, preserving the
    current version, version history and etag. Successful writes refresh the
    last-updated timestamp.

    Example:
    ::

        $ python manage.py archive:set_expiry --desk Sports --days 999
        $ python manage.py archive:set_expiry --desk Sports --days 999 --from-updated
        $ python manage.py archive:set_expiry --desk "Sports News"

    """

    option_list = [
        superdesk.Option("--desk", required=True, help="Exact desk name"),
        superdesk.Option("--days", type=int, default=None, help="Expiry duration in days (positive integer)"),
        superdesk.Option(
            "--from-updated",
            action="store_true",
            default=False,
            help="Calculate expiry from each item's last update instead of now",
        ),
    ]
    batch_size = 500

    def run(self, desk: str, days: int | None = None, from_updated: bool = False) -> int:
        if days is not None and days <= 0:
            raise ValueError("--days must be a positive integer")

        desk_doc = get_resource_service("desks").find_one(req=None, name=desk)
        if desk_doc is None:
            raise ValueError("Desk not found: {}".format(desk))

        now = utcnow()
        archive_service = get_resource_service(ARCHIVE)
        lookup = {
            "task.desk": desk_doc[config.ID_FIELD],
            ITEM_STATE: {
                "$in": [
                    CONTENT_STATE.DRAFT,
                    CONTENT_STATE.INGESTED,
                    CONTENT_STATE.ROUTED,
                    CONTENT_STATE.FETCHED,
                    CONTENT_STATE.SUBMITTED,
                    CONTENT_STATE.PROGRESS,
                ]
            },
        }
        count = 0
        skipped = 0
        conflicts = 0
        stages = {}
        while True:
            items = list(archive_service.find(lookup, max_results=self.batch_size, sort="_id"))
            if not items:
                break
            for item in items:
                try:
                    updated = item.get(config.LAST_UPDATED)
                    if from_updated and not isinstance(updated, datetime):
                        raise ValueError("Invalid last-updated timestamp")
                    offset = updated if from_updated else now
                    if days is not None:
                        item_expiry = get_expiry_date(days * 24 * 60, offset=offset)
                    else:
                        stage_id = item.get("task", {}).get("stage")
                        stage = None
                        if stage_id:
                            if stage_id not in stages:
                                stages[stage_id] = get_resource_service("stages").find_one(req=None, _id=stage_id)
                            stage = stages[stage_id]
                            if not stage:
                                logger.error(
                                    "Skipping expiry update for item %s on desk %r: Invalid stage identifier %s",
                                    item[config.ID_FIELD],
                                    desk,
                                    stage_id,
                                )
                                skipped += 1
                                continue
                        item_expiry = get_item_expiry(desk_doc, stage, offset=offset)
                except (KeyError, TypeError, ValueError, OverflowError, SuperdeskApiError):
                    logger.exception("Skipping expiry update for item %s on desk %r", item[config.ID_FIELD], desk)
                    skipped += 1
                    continue
                try:
                    archive_service.system_update(item[config.ID_FIELD], {"expiry": item_expiry}, item, check_etag=True)
                except UpdateConflictError:
                    logger.warning(
                        "Skipping expiry update for changed or removed item %s on desk %r", item[config.ID_FIELD], desk
                    )
                    conflicts += 1
                    continue
                count += 1
            lookup[config.ID_FIELD] = {"$gt": items[-1][config.ID_FIELD]}

        print("Updated expiry on {} items on desk {!r}.".format(count, desk))
        if skipped:
            print("Skipped {} items with expiry errors; see logs for details.".format(skipped))
        if conflicts:
            print("Skipped {} items changed or removed concurrently; see logs for details.".format(conflicts))
        return count

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from superdesk.flask import request
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import (
    CONTENT_TYPE,
    ITEM_TYPE,
    ITEM_STATE,
    CONTENT_STATE,
    PUBLISH_SCHEDULE,
    EMBARGO,
    SCHEDULE_SETTINGS,
    ASSOCIATIONS,
)

from apps.archive.common import set_sign_off, ITEM_OPERATION
from apps.archive.archive import update_word_count
from superdesk.lifecycle_timing import duration_ms, to_epoch_ms, duration_ms_from_epoch
from datetime import datetime

from superdesk.utc import utcnow
from superdesk.publish_async.utils import get_residrefs

from .common import BasePublishService, BasePublishResource, ITEM_PUBLISH
from quart_babel import gettext as _

logger = logging.getLogger(__name__)


class ArchivePublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, "publish")


class ArchivePublishService(BasePublishService):
    """
    Handles publishing and scheduling operations for archive items.

    Set's the ``_state`` field to ``published``.

    :raises:
        - :class:`superdesk.errors.SuperdeskApiError.badRequestError`
            If the item is package and contains no items.
    """

    publish_type = "publish"
    published_state = "published"
    item_operation = ITEM_PUBLISH

    async def _validate(self, original, updates):
        await super()._validate(original, updates)
        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            items = get_residrefs(original)

            if len(items) == 0 and self.publish_type == ITEM_PUBLISH:
                raise SuperdeskApiError.badRequestError(_("Empty package cannot be published!"))

    def _set_first_published(self, updates: dict, original: dict) -> datetime | None:
        """Set ``firstpublished`` on updates and return a ms-precision datetime for lifecycle timing.

        Returns the ms-precision publish datetime, or ``None`` if ``firstpublished`` was already set.
        """
        if original.get("firstpublished"):
            return None
        if updates.get(SCHEDULE_SETTINGS) and updates[SCHEDULE_SETTINGS].get("utc_publish_schedule"):
            updates["firstpublished"] = updates[SCHEDULE_SETTINGS]["utc_publish_schedule"]
            return None
        first_published_dt = utcnow(microseconds=True)
        updates["firstpublished"] = first_published_dt.replace(microsecond=0)
        return first_published_dt

    def _update_lifecycle_timing(self, updates: dict, original: dict, first_published_dt: datetime | None) -> None:
        """Merge and populate ``lifecycle_timing`` on the first publish of an item."""
        # Preserve existing lifecycle timing fields from the original document.
        # Without this merge, setting updates["lifecycle_timing"] would replace
        # the full object and drop ingest timestamps.
        lifecycle_timing = dict(original.get("lifecycle_timing") or {})
        lifecycle_timing.update(updates.get("lifecycle_timing") or {})
        updates["lifecycle_timing"] = lifecycle_timing

        if "first_published_at" in lifecycle_timing:
            return

        # Use ms-precision datetime for lifecycle timing; fall back to firstpublished for scheduled items.
        first_pub_dt = first_published_dt or updates["firstpublished"]
        lifecycle_timing["first_published_at"] = first_pub_dt
        lifecycle_timing["first_published_ms"] = to_epoch_ms(first_pub_dt)

        if not lifecycle_timing.get("lifecycle_started_at"):
            lifecycle_timing["lifecycle_started_at"] = lifecycle_timing["first_published_at"]
        if not isinstance(lifecycle_timing.get("lifecycle_started_ms"), int):
            lifecycle_timing["lifecycle_started_ms"] = to_epoch_ms(lifecycle_timing["lifecycle_started_at"])

        started_ms = lifecycle_timing.get("lifecycle_started_ms")
        finished_ms = lifecycle_timing.get("first_published_ms")
        if isinstance(started_ms, int) and isinstance(finished_ms, int):
            lifecycle_timing["lifecycle_to_first_publish_ms"] = duration_ms_from_epoch(started_ms, finished_ms)
        else:
            start_time = lifecycle_timing.get("lifecycle_started_at")
            if start_time:
                lifecycle_timing["lifecycle_to_first_publish_ms"] = duration_ms(
                    start_time, lifecycle_timing["first_published_at"]
                )

    async def on_update_async(self, updates, original):
        updates[ITEM_OPERATION] = self.item_operation
        await super().on_update_async(updates, original)

        is_first_publish = not original.get("firstpublished") and not updates.get("firstpublished")
        first_published_dt = self._set_first_published(updates, original)

        if is_first_publish and updates.get("firstpublished"):
            self._update_lifecycle_timing(updates, original, first_published_dt)

        if original.get("marked_for_user"):
            # remove marked_for_user on publish and keep it as previous_marked_user for history
            updates["previous_marked_user"] = original["marked_for_user"]
            updates["marked_for_user"] = None
            updates["marked_for_sign_off"] = None

        set_sign_off(updates, original)
        update_word_count(updates)
        self.set_desk(updates, original)

    def set_state(self, original, updates):
        """Set the state of the document to schedule if the publish_schedule is specified.

        :param dict original: original document
        :param dict updates: updates related to original document
        """
        updates.setdefault(ITEM_OPERATION, ITEM_PUBLISH)
        if updates.get(PUBLISH_SCHEDULE):
            updates[ITEM_STATE] = CONTENT_STATE.SCHEDULED
        elif original.get(EMBARGO) or updates.get(EMBARGO):
            updates[ITEM_STATE] = CONTENT_STATE.PUBLISHED
        else:
            super().set_state(original, updates)

    def set_desk(self, updates, original):
        if (
            not original.get("task", {}).get("desk")
            and not updates.get("task", {}).get("desk")
            and request
            and request.args
            and request.args.get("desk_id")
        ):
            desk_id = request.args["desk_id"]
            updates["task"] = updates.get("task", original.get("task", {}))
            updates["task"]["desk"] = desk_id

            if updates.get(ASSOCIATIONS):
                for key, associated_item in updates[ASSOCIATIONS].items():
                    if associated_item and not associated_item.get("task", {}).get("desk"):
                        associated_item["task"] = associated_item.get("task", {})
                        associated_item["task"]["desk"] = desk_id

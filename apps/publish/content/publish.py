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
from superdesk.utc import utcnow

from .common import BasePublishService, BasePublishResource, ITEM_PUBLISH
from flask_babel import _
from flask import request

logger = logging.getLogger(__name__)


class ArchivePublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, "publish")


class ArchivePublishService(BasePublishService):
    publish_type = "publish"
    published_state = "published"
    item_operation = ITEM_PUBLISH

    def _validate(self, original, updates):
        super()._validate(original, updates)
        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            items = self.package_service.get_residrefs(original)

            if len(items) == 0 and self.publish_type == ITEM_PUBLISH:
                raise SuperdeskApiError.badRequestError(_("Empty package cannot be published!"))

    def on_update(self, updates, original):
        updates[ITEM_OPERATION] = self.item_operation
        super().on_update(updates, original)

        if not original.get("firstpublished"):
            if updates.get(SCHEDULE_SETTINGS) and updates[SCHEDULE_SETTINGS].get("utc_publish_schedule"):
                updates["firstpublished"] = updates[SCHEDULE_SETTINGS]["utc_publish_schedule"]
            else:
                updates["firstpublished"] = utcnow()

        if original.get("marked_for_user"):
            # remove marked_for_user on publish and keep it as previous_marked_user for history
            updates["previous_marked_user"] = original["marked_for_user"]
            updates["marked_for_user"] = None

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

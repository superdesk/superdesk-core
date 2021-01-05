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
from eve.utils import config
from copy import deepcopy

from superdesk import get_resource_service
from superdesk.resource import Resource
from superdesk.services import BaseService
from apps.archive.common import ITEM_UPDATE, get_user, ITEM_CREATE, ITEM_FETCH
from superdesk.metadata.item import CONTENT_STATE, ITEM_STATE
from superdesk.utc import utcnow
from apps.item_lock.components.item_lock import LOCK_USER, LOCK_SESSION, LOCK_ACTION, LOCK_TIME

log = logging.getLogger(__name__)

fields_to_remove = [
    "_id",
    "_etag",
    "versioncreator",
    "originalcreator",
    "versioncreated",
    "_current_version",
    "version",
    "_updated",
    "lock_session",
    "lock_user",
    "lock_time",
    "lock_action",
    "force_unlock",
    "_created",
    "guid",
    "family_id",
    "firstcreated",
    "original_creator",
]


class ArchiveHistoryResource(Resource):
    endpoint_name = "archive_history"
    resource_methods = ["GET"]
    item_methods = ["GET"]
    schema = {
        "item_id": {"type": "string"},
        "user_id": Resource.rel("users", True),
        "operation": {"type": "string"},
        "update": {"type": "dict", "nullable": True},
        "version": {"type": "integer"},
        "original_item_id": {"type": "string"},
    }

    mongo_indexes = {
        "item_id": ([("item_id", 1)], {"background": True}),
        "_id_document": ([("_id_document", 1)], {"background": True}),
    }


class ArchiveHistoryService(BaseService):
    def on_item_updated(self, updates, original, operation=None):
        item = deepcopy(original)
        if updates:
            item.update(updates)

        if operation in [ITEM_CREATE, ITEM_FETCH]:
            # If this is the initial create on the item,
            # then store the metadata from original as well
            self._save_history(item, item, operation)
        else:
            self._save_history(item, updates, operation or ITEM_UPDATE)

    def on_item_deleted(self, doc):
        lookup = {"item_id": doc[config.ID_FIELD]}
        self.delete(lookup=lookup)

    def on_item_locked(self, item, user_id):
        self._save_lock_history(item, "item_lock")

    def on_item_unlocked(self, item, user_id):
        if item.get(config.VERSION, 1) == 0:
            # version 0 items get deleted on unlock, along with all history documents
            # so there is no need to record a history item here
            return

        self._save_lock_history(item, "item_unlock")

    def _save_lock_history(self, item, operation):
        self.post(
            [
                {
                    "item_id": item[config.ID_FIELD],
                    "user_id": self.get_user_id(item),
                    "operation": operation,
                    "update": {
                        LOCK_USER: item.get(LOCK_USER),
                        LOCK_SESSION: item.get(LOCK_SESSION),
                        LOCK_ACTION: item.get(LOCK_ACTION),
                        LOCK_TIME: item.get(LOCK_TIME),
                    },
                    "version": item.get(config.VERSION, 1),
                }
            ]
        )

    def get_user_id(self, item):
        user = get_user()
        if user:
            return user.get(config.ID_FIELD)

    def _save_history(self, item, update, operation):
        # in case of auto-routing, if the original_creator exists in our database
        # then create item create record in the archive history.
        if (
            item.get(ITEM_STATE) == CONTENT_STATE.ROUTED
            and item.get("original_creator")
            and not item.get("original_id")
        ):
            user = get_resource_service("users").find_one(req=None, _id=item.get("original_creator"))
            firstcreated = item.get("firstcreated", utcnow())

            if user:
                history = {
                    "item_id": item[config.ID_FIELD],
                    "user_id": user.get(config.ID_FIELD),
                    "operation": ITEM_CREATE,
                    "update": self._remove_unwanted_fields(update, item),
                    "version": item.get(config.VERSION, 1),
                    "_created": firstcreated,
                    "_updated": firstcreated,
                }

                self.post([history])

        history = {
            "item_id": item[config.ID_FIELD],
            "user_id": self.get_user_id(item),
            "operation": operation,
            "update": self._remove_unwanted_fields(update, item),
            "version": item.get(config.VERSION, 1),
        }

        self.post([history])

    def _remove_unwanted_fields(self, update, original):
        if update:
            update_copy = deepcopy(update)
            for field in fields_to_remove:
                update_copy.pop(field, None)

            if original.get("sms_message") == update_copy.get("sms_message"):
                update_copy.pop("sms_message", None)

            return update_copy

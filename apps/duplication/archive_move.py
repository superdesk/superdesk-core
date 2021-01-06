# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
import superdesk.signals as signals

from eve.utils import config
from eve.versioning import resolve_document_version
from flask import request, current_app as app
from copy import deepcopy

from apps.tasks import send_to, apply_onstage_rule
from apps.desks import DeskTypes
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.metadata.item import (
    ITEM_STATE,
    CONTENT_STATE,
    SIGN_OFF,
    LAST_AUTHORING_DESK,
    LAST_PRODUCTION_DESK,
    LAST_DESK,
    DESK_HISTORY,
)
from superdesk.metadata.packages import REFS, GROUPS, RESIDREF
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.metadata.utils import item_url
from apps.archive.common import (
    insert_into_versions,
    item_operations,
    ITEM_OPERATION,
    set_sign_off,
    get_user,
    convert_task_attributes_to_objectId,
)
from apps.archive.archive import SOURCE as ARCHIVE
from superdesk.workflow import is_workflow_state_transition_valid
from apps.content import push_item_move_notification
from superdesk.lock import lock, unlock
from flask_babel import _

ITEM_MOVE = "move"
item_operations.append(ITEM_MOVE)


class MoveResource(Resource):
    endpoint_name = "move"
    resource_title = endpoint_name

    schema = {
        "task": {
            "type": "dict",
            "required": False,
            "schema": {
                "desk": Resource.rel("desks", False, required=True),
                "stage": Resource.rel("stages", False, required=True),
            },
        },
        "allPackageItems": {"type": "boolean", "required": False, "nullable": True},
    }

    url = "archive/<{0}:guid>/move".format(item_url)

    resource_methods = ["POST"]
    item_methods = []

    privileges = {"POST": "archive"}


class MoveService(BaseService):
    def create(self, docs, **kwargs):
        guid_of_item_to_be_moved = request.view_args["guid"]
        guid_of_moved_items = []

        # set the lock_id it per item
        lock_id = "item_move {}".format(guid_of_item_to_be_moved)

        if not lock(lock_id, expire=5):
            raise SuperdeskApiError.forbiddenError(message=_("Item is locked for move by another user."))

        try:
            # doc represents the target desk and stage
            doc = docs[0]
            moved_item = self.move_content(guid_of_item_to_be_moved, doc)
            guid_of_moved_items.append(moved_item.get(config.ID_FIELD))

            if moved_item.get("type", None) == "composite" and doc.get("allPackageItems", False):
                try:
                    item_lock_id = None
                    for item_id in (
                        ref[RESIDREF]
                        for group in moved_item.get(GROUPS, [])
                        for ref in group.get(REFS, [])
                        if RESIDREF in ref
                    ):
                        item_lock_id = "item_move {}".format(item_id)
                        if lock(item_lock_id, expire=5):
                            item = self.move_content(item_id, doc)
                            guid_of_moved_items.append(item.get(config.ID_FIELD))
                            unlock(item_lock_id, remove=True)
                            item_lock_id = None
                        else:
                            item_lock_id = None
                finally:
                    if item_lock_id:
                        unlock(item_lock_id, remove=True)

            return guid_of_moved_items
        finally:
            unlock(lock_id, remove=True)

    def move_content(self, id, doc):
        archive_service = get_resource_service(ARCHIVE)
        archived_doc = archive_service.find_one(req=None, _id=id)

        if not archived_doc:
            raise SuperdeskApiError.notFoundError(_("Fail to found item with guid: {guid}").format(guid=id))

        self._validate(archived_doc, doc)
        self._move(archived_doc, doc)

        # get the recent updates again
        archived_doc = archive_service.find_one(req=None, _id=id)
        # finally apply any on stage rules/macros
        apply_onstage_rule(archived_doc, id)

        return archived_doc

    def _move(self, archived_doc, doc):
        archive_service = get_resource_service(ARCHIVE)
        original = deepcopy(archived_doc)
        user = get_user()
        send_to(
            doc=archived_doc,
            desk_id=doc.get("task", {}).get("desk"),
            stage_id=doc.get("task", {}).get("stage"),
            user_id=user.get(config.ID_FIELD),
        )
        if archived_doc[ITEM_STATE] not in (
            {
                CONTENT_STATE.PUBLISHED,
                CONTENT_STATE.SCHEDULED,
                CONTENT_STATE.KILLED,
                CONTENT_STATE.RECALLED,
                CONTENT_STATE.CORRECTION,
            }
        ):
            archived_doc[ITEM_STATE] = CONTENT_STATE.SUBMITTED
        archived_doc[ITEM_OPERATION] = ITEM_MOVE
        # set the change in desk type when content is moved.
        self.set_change_in_desk_type(archived_doc, original)
        archived_doc.pop(SIGN_OFF, None)
        set_sign_off(archived_doc, original=original)
        convert_task_attributes_to_objectId(archived_doc)
        resolve_document_version(archived_doc, ARCHIVE, "PATCH", original)

        del archived_doc[config.ID_FIELD]
        del archived_doc[config.ETAG]  # force etag update

        signals.item_move.send(self, item=archived_doc, original=original)
        archive_service.update(original[config.ID_FIELD], archived_doc, original)

        insert_into_versions(id_=original[config.ID_FIELD])
        push_item_move_notification(original, archived_doc)
        app.on_archive_item_updated(archived_doc, original, ITEM_MOVE)

        # make sure `item._id` is there in signal
        moved_item = archived_doc.copy()
        moved_item[config.ID_FIELD] = original[config.ID_FIELD]
        signals.item_moved.send(self, item=moved_item, original=original)

    def _validate(self, archived_doc, doc):
        """Validate that the item can be move.

        :param dict archived_doc: item to be moved
        :param dict doc: new location details
        """
        current_stage_of_item = archived_doc.get("task", {}).get("stage")
        if current_stage_of_item and str(current_stage_of_item) == str(doc.get("task", {}).get("stage")):
            raise SuperdeskApiError.preconditionFailedError(message=_("Move is not allowed within the same stage."))
        if not is_workflow_state_transition_valid("submit_to_desk", archived_doc[ITEM_STATE]):
            raise InvalidStateTransitionError()

    def set_change_in_desk_type(self, updated, original):
        """Detects if the change in the desk is between authoring to production (and vice versa).

        Sets the field 'last_production_desk' and 'last_authoring_desk'.

        :param dict updated: document to be saved
        :param dict original: original document
        """
        old_desk_id = str(original.get("task", {}).get("desk", ""))
        new_desk_id = str(updated.get("task", {}).get("desk", ""))
        if old_desk_id and old_desk_id != new_desk_id:
            old_desk = get_resource_service("desks").find_one(req=None, _id=old_desk_id)
            new_desk = get_resource_service("desks").find_one(req=None, _id=new_desk_id)
            if old_desk and new_desk and old_desk.get("desk_type", "") != new_desk.get("desk_type", ""):
                if new_desk.get("desk_type") == DeskTypes.production.value:
                    updated["task"][LAST_AUTHORING_DESK] = old_desk_id
                else:
                    updated["task"][LAST_PRODUCTION_DESK] = old_desk_id
            updated["task"][LAST_DESK] = old_desk_id
            updated["task"].setdefault(DESK_HISTORY, [])
            if old_desk_id not in updated["task"][DESK_HISTORY]:
                updated["task"][DESK_HISTORY].append(old_desk_id)


superdesk.workflow_action(
    name="submit_to_desk",
    include_states=[
        "draft",
        "fetched",
        "routed",
        "submitted",
        "in_progress",
        "published",
        "scheduled",
        "unpublished",
        "correction",
    ],
    privileges=["archive"],
)

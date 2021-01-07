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

from flask import request, current_app as app
from flask_babel import _
from eve.utils import config

from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE
from superdesk.notification import push_notification
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.metadata.utils import item_url
from superdesk.workflow import is_workflow_state_transition_valid
from apps.auth import get_user, get_user_id
from apps.archive.archive import SOURCE as ARCHIVE


class CopyResource(Resource):
    endpoint_name = "copy"
    resource_title = endpoint_name

    # Eve needs schema definition even if all the properties are optional.
    schema = {"desk": Resource.rel("desks", False, required=False)}

    url = "archive/<{0}:guid>/copy".format(item_url)

    resource_methods = ["POST"]
    item_methods = []


class CopyService(BaseService):
    def create(self, docs, **kwargs):
        guid_of_item_to_be_copied = request.view_args["guid"]

        guid_of_copied_items = []

        for doc in docs:
            archive_service = get_resource_service(ARCHIVE)

            archived_doc = archive_service.find_one(req=None, _id=guid_of_item_to_be_copied)
            if not archived_doc:
                raise SuperdeskApiError.notFoundError(
                    _("Fail to found item with guid: {guid}").format(guid=guid_of_item_to_be_copied)
                )

            current_desk_of_item = archived_doc.get("task", {}).get("desk")
            if current_desk_of_item and not app.config["WORKFLOW_ALLOW_COPY_TO_PERSONAL"]:
                raise SuperdeskApiError.preconditionFailedError(message=_("Copy is not allowed on items in a desk."))
            elif current_desk_of_item:
                archived_doc["task"] = {}
                archived_doc["original_creator"] = get_user_id()

            if not is_workflow_state_transition_valid("copy", archived_doc[ITEM_STATE]):
                raise InvalidStateTransitionError()

            new_guid = archive_service.duplicate_content(archived_doc)
            guid_of_copied_items.append(new_guid)

        if kwargs.get("notify", True):
            user = get_user()
            push_notification("item:copy", copied=1, user=str(user.get(config.ID_FIELD, "")))

        return guid_of_copied_items


def init_app(app):
    if app.config["WORKFLOW_ALLOW_COPY_TO_PERSONAL"]:
        kwargs = dict(
            exclude_states=[CONTENT_STATE.SPIKED, CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED],
        )
    else:
        kwargs = dict(
            include_states=[CONTENT_STATE.DRAFT],
        )
    superdesk.workflow_action(
        name="copy",
        privileges=["archive"],
        **kwargs,
    )
    app.client_config["workflow_allow_copy_to_personal"] = app.config["WORKFLOW_ALLOW_COPY_TO_PERSONAL"]

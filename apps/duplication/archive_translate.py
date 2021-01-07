# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import superdesk
from apps.archive.archive import SOURCE as ARCHIVE
from apps.content import push_content_notification
from apps.auth import get_user_id
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.metadata.item import CONTENT_STATE, ITEM_STATE
from superdesk.metadata.packages import RESIDREF
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk.utc import utcnow
from apps.packages import PackageService
from flask_babel import _
from flask import current_app as app


package_service = PackageService()


class TranslateResource(Resource):
    endpoint_name = "translate"
    resource_title = endpoint_name

    schema = {
        "guid": {"type": "string", "required": True},
        "language": {"type": "string", "required": True},
        "desk": Resource.rel("desks", nullable=True),
    }

    url = "archive/translate"

    resource_methods = ["POST"]
    item_methods = []

    privileges = {"POST": "translate"}


class TranslateService(BaseService):
    def _translate_item(self, guid, language, task=None, service=None, state=None, **kwargs):
        if not service:
            service = ARCHIVE
        archive_service = get_resource_service(service)
        macros_service = get_resource_service("macros")
        published_service = get_resource_service("published")

        item = archive_service.find_one(req=None, guid=guid)
        if not item:
            raise SuperdeskApiError.notFoundError(_("Fail to found item with guid: {guid}").format(guid=guid))

        if not is_workflow_state_transition_valid("translate", item[ITEM_STATE]):
            raise InvalidStateTransitionError()

        if item.get("language") == language:
            return guid

        if package_service.is_package(item):
            refs = package_service.get_item_refs(item)
            for ref in refs:
                ref[RESIDREF] = self._translate_item(ref[RESIDREF], language, service=ref.get("location"), task=task)

        if not item.get("translation_id"):
            item["translation_id"] = item["guid"]

        macros_service.execute_translation_macro(item, item.get("language", None), language)

        item["language"] = language
        item["translated_from"] = guid
        item["versioncreated"] = utcnow()
        item["firstcreated"] = utcnow()
        if task:
            item["task"] = task

        extra_fields = ["translation_id", "translated_from"]

        UPDATE_TRANSLATION_METADATA_MACRO = app.config.get("UPDATE_TRANSLATION_METADATA_MACRO")

        if UPDATE_TRANSLATION_METADATA_MACRO and macros_service.get_macro_by_name(UPDATE_TRANSLATION_METADATA_MACRO):
            macros_service.execute_macro(item, UPDATE_TRANSLATION_METADATA_MACRO)

        translation_guid = archive_service.duplicate_item(
            item, extra_fields=extra_fields, state=state, operation="translate"
        )

        item.setdefault("translations", []).append(translation_guid)

        updates = {
            "translation_id": item["translation_id"],
            "translations": item["translations"],
        }

        archive_service.system_update(item["_id"], updates, item)
        published_service.update_published_items(item["_id"], "translation_id", item["_id"])
        published_service.update_published_items(item["_id"], "translations", item["translations"])

        if kwargs.get("notify", True):
            push_content_notification([item])

        return translation_guid

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            task = None
            if doc.get("desk"):
                desk = get_resource_service("desks").find_one(req=None, _id=doc["desk"]) or {}
                task = dict(desk=desk.get("_id"), stage=desk.get("working_stage"), user=get_user_id())
            ids.append(self._translate_item(doc["guid"], doc["language"], task, **kwargs))
        return ids


superdesk.workflow_action(
    name="translate",
    exclude_states=[CONTENT_STATE.SPIKED, CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED],
    privileges=["archive", "translate"],
)

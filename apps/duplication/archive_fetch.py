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

from copy import deepcopy
from flask import request
from flask_babel import _
from eve.utils import config

from apps.archive.usage import update_refs
from apps.archive.archive import SOURCE as ARCHIVE
from apps.content import push_item_move_notification
from superdesk.metadata.utils import item_url
from apps.archive.common import insert_into_versions, fetch_item
from superdesk.metadata.item import INGEST_ID, INGEST_VERSION, FAMILY_ID, ITEM_STATE, CONTENT_STATE, GUID_FIELD
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.resource import Resource, build_custom_hateoas
from superdesk.services import BaseService
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk import get_resource_service
from superdesk.metadata.packages import RESIDREF, REFS, GROUPS
from superdesk.metadata.item import MEDIA_TYPES, ASSOCIATIONS, get_schema

custom_hateoas = {"self": {"title": "Archive", "href": "/archive/{_id}"}}


class FetchResource(Resource):
    endpoint_name = "fetch"
    resource_title = endpoint_name

    schema = get_schema(True)
    schema.update(
        {
            "desk": Resource.rel("desks", False, required=True),
            "stage": Resource.rel("stages", False, nullable=True),
            "macro": {"type": "string"},
            "_links": {"type": "dict"},
        }
    )

    url = "ingest/<{0}:id>/fetch".format(item_url)

    resource_methods = ["POST"]
    item_methods = []

    privileges = {"POST": "fetch"}


class FetchService(BaseService):
    def create(self, docs, **kwargs):
        return self.fetch(docs, id=request.view_args.get("id"), **kwargs)

    def fetch(self, docs, id=None, **kwargs):
        id_of_fetched_items = []

        for doc in docs:
            id_of_item_to_be_fetched = doc.get(config.ID_FIELD) if id is None else id

            desk_id = doc.get("desk")
            stage_id = doc.get("stage")

            ingest_service = get_resource_service("ingest")
            ingest_doc = ingest_service.find_one(req=None, _id=id_of_item_to_be_fetched)

            if not ingest_doc:
                raise SuperdeskApiError.notFoundError(
                    _("Fail to found ingest item with _id: {id}").format(id=id_of_item_to_be_fetched)
                )

            if not is_workflow_state_transition_valid("fetch_from_ingest", ingest_doc[ITEM_STATE]):
                raise InvalidStateTransitionError()

            if doc.get("macro"):  # there is a macro so transform it
                macro_kwargs = kwargs.get("macro_kwargs") or {}
                ingest_doc = get_resource_service("macros").execute_macro(
                    ingest_doc,
                    doc.get("macro"),
                    dest_desk_id=desk_id,
                    dest_stage_id=stage_id,
                    **macro_kwargs,
                )

            dest_doc = fetch_item(
                ingest_doc,
                desk_id,
                stage_id,
                # we might want to change state or target from the macro
                state=ingest_doc[ITEM_STATE]
                if ingest_doc.get(ITEM_STATE) and ingest_doc[ITEM_STATE] != CONTENT_STATE.INGESTED
                else doc.get(ITEM_STATE),
                target=ingest_doc.get("target", doc.get("target")),
            )

            id_of_fetched_items.append(dest_doc[config.ID_FIELD])
            ingest_service.patch(id_of_item_to_be_fetched, {"archived": dest_doc["versioncreated"]})

            dest_doc[FAMILY_ID] = ingest_doc[config.ID_FIELD]
            dest_doc[INGEST_ID] = self.__strip_version_from_guid(ingest_doc[GUID_FIELD], ingest_doc.get("version"))
            dest_doc[INGEST_VERSION] = ingest_doc.get("version")

            self.__fetch_items_in_package(dest_doc, desk_id, stage_id, doc.get(ITEM_STATE, CONTENT_STATE.FETCHED))

            self.__fetch_associated_items(dest_doc, desk_id, stage_id, doc.get(ITEM_STATE, CONTENT_STATE.FETCHED))

            desk = get_resource_service("desks").find_one(req=None, _id=desk_id)
            if desk and desk.get("default_content_profile"):
                dest_doc.setdefault("profile", desk["default_content_profile"])

            if dest_doc.get("type", "text") in MEDIA_TYPES:
                dest_doc["profile"] = None

            update_refs(dest_doc, {})

            get_resource_service(ARCHIVE).post([dest_doc])
            insert_into_versions(doc=dest_doc)
            build_custom_hateoas(custom_hateoas, dest_doc)
            superdesk.item_fetched.send(self, item=dest_doc, ingest_item=ingest_doc)
            doc.update(dest_doc)

        if kwargs.get("notify", True):
            ingest_doc.update({"task": dest_doc.get("task")})
            push_item_move_notification(ingest_doc, doc, "item:fetch")

        return id_of_fetched_items

    def __strip_version_from_guid(self, guid, version):
        """
        Checks if guid contains the version for the ingested item and returns the guid without version
        """
        try:
            if not version:
                return guid

            if guid.endswith(":{}".format(str(version))):
                return guid[: -1 * (len(str(version)) + 1)]
        except Exception:
            return guid

    def __fetch_associated_items(self, doc, desk, stage, state):
        """
        Fetches the associated items of a given document
        """
        for key, item in (doc.get(ASSOCIATIONS) or {}).items():
            if item is not None and item.get("state") == "ingested":
                new_item = deepcopy(item)
                new_item["desk"] = desk
                new_item["stage"] = stage
                new_item["state"] = state
                new_ids = self.fetch([new_item], id=None, notify=False)
                item[config.ID_FIELD] = new_ids[0]

    def __fetch_items_in_package(self, dest_doc, desk, stage, state):
        # Note: macro and target information is not user for package publishing.
        # Needs to looked later when package ingest requirements is clear.
        for ref in [ref for group in dest_doc.get(GROUPS, []) for ref in group.get(REFS, []) if ref.get(RESIDREF)]:
            ref["location"] = ARCHIVE

        refs = [
            {config.ID_FIELD: ref.get(RESIDREF), "desk": desk, "stage": stage, ITEM_STATE: state}
            for group in dest_doc.get(GROUPS, [])
            for ref in group.get(REFS, [])
            if ref.get(RESIDREF)
        ]

        if refs:
            new_ref_guids = self.fetch(refs, id=None, notify=False)
            count = 0
            for ref in [ref for group in dest_doc.get(GROUPS, []) for ref in group.get(REFS, []) if ref.get(RESIDREF)]:
                ref[RESIDREF] = ref[GUID_FIELD] = new_ref_guids[count]
                count += 1


superdesk.workflow_state(CONTENT_STATE.FETCHED)
superdesk.workflow_action(
    name="fetch_from_ingest", include_states=["ingested"], privileges=["ingest", "archive", "fetch"]
)

superdesk.workflow_state("routed")
superdesk.workflow_action(name="route", include_states=["ingested"])

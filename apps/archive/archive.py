# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
import logging
import datetime
import superdesk
import superdesk.signals as signals
from superdesk import editor_utils

from copy import copy, deepcopy
from superdesk.resource import Resource
from superdesk.metadata.utils import (
    extra_response_fields,
    item_url,
    aggregations,
    is_normal_package,
    get_elastic_highlight_query,
)
from .common import (
    remove_unwanted,
    update_state,
    set_item_expiry,
    remove_media_files,
    on_create_item,
    on_duplicate_item,
    get_user,
    update_version,
    set_sign_off,
    handle_existing_data,
    item_schema,
    validate_schedule,
    is_item_in_package,
    update_schedule_settings,
    ITEM_OPERATION,
    ITEM_RESTORE,
    ITEM_CREATE,
    ITEM_UPDATE,
    ITEM_DUPLICATE,
    ITEM_DUPLICATED_FROM,
    ITEM_DESCHEDULE,
    ARCHIVE as SOURCE,
    LAST_PRODUCTION_DESK,
    LAST_AUTHORING_DESK,
    ITEM_FETCH,
    convert_task_attributes_to_objectId,
    BROADCAST_GENRE,
    set_dateline,
    get_subject,
    transtype_metadata,
)
from superdesk.media.crop import CropService
from flask import current_app as app, json
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from eve.versioning import resolve_document_version, versioned_id_field
from superdesk.activity import add_activity, notify_and_add_activity, ACTIVITY_CREATE, ACTIVITY_UPDATE, ACTIVITY_DELETE
from eve.utils import parse_request, config, date_to_str, ParsedRequest
from superdesk.services import BaseService
from superdesk.users.services import current_user_has_privilege, is_admin
from superdesk.metadata.item import (
    ITEM_STATE,
    CONTENT_STATE,
    CONTENT_TYPE,
    ITEM_TYPE,
    EMBARGO,
    PUBLISH_SCHEDULE,
    SCHEDULE_SETTINGS,
    SIGN_OFF,
    ASSOCIATIONS,
    MEDIA_TYPES,
    INGEST_ID,
    PROCESSED_FROM,
    PUBLISH_STATES,
    get_schema,
)
from superdesk.metadata.packages import LINKED_IN_PACKAGES, RESIDREF
from apps.common.components.utils import get_component
from apps.item_autosave.components.item_autosave import ItemAutosave
from apps.common.models.base_model import InvalidEtag
from superdesk.text_utils import update_word_count
from apps.content import push_content_notification, push_expired_notification, push_notification
from apps.common.models.utils import get_model
from apps.item_lock.models.item import ItemModel
from apps.packages import PackageService
from .archive_media import ArchiveMediaService
from .usage import track_usage, update_refs
from superdesk.utc import utcnow
from superdesk.vocabularies import is_related_content
from flask_babel import _

EDITOR_KEY_PREFIX = "editor_"
logger = logging.getLogger(__name__)


def format_subj_qcode(subj):
    return ":".join([code for code in [subj.get("scheme"), subj.get("qcode")] if code])


def private_content_filter():
    """Filter out out users private content if this is a user request.

    As private we treat items where user is creator, last version creator,
    or has the item assigned to him atm.

    Also filter out content of stages not visible to current user (if any).
    """
    user = getattr(flask.g, "user", None)
    if user:
        private_filter = {
            "should": [
                {"exists": {"field": "task.desk"}},
                {"term": {"task.user": str(user["_id"])}},
                {"term": {"version_creator": str(user["_id"])}},
                {"term": {"original_creator": str(user["_id"])}},
            ],
            "minimum_should_match": 1,
        }

        if "invisible_stages" in user:
            stages = user.get("invisible_stages")
        else:
            stages = get_resource_service("users").get_invisible_stages_ids(user.get("_id"))

        if stages:
            private_filter["must_not"] = [{"terms": {"task.stage": stages}}]

        # user can see all public content
        # as long as it's not drafts
        private_filter["should"].append(
            {
                "bool": {
                    "must": {"exists": {"field": "task.desk"}},
                    "must_not": {"term": {"state": "draft"}},
                }
            }
        )

        return {
            "bool": {
                "should": [
                    {"bool": private_filter},
                    {"bool": {"must_not": {"term": {"state": "draft"}}}},
                ],
                "minimum_should_match": 1,
            },
        }
    else:  # no user specific filtering, filter out private content
        return {
            "bool": {
                "must": {"exists": {"field": "task.desk"}},
                "must_not": {"term": {"state": "draft"}},
            },
        }


def update_image_caption(body, name, caption):
    # Note: because of Tansa the image caption from association is updated but
    # the related image caption from body_html is not updated
    start = body.find(name)
    if start == -1:
        return body
    startDescription = body.find("<figcaption>", start)
    endDescription = body.find("</figcaption>", start)
    if startDescription == -1 or endDescription == -1:
        return body
    return body[0 : startDescription + len("<figcaption>")] + caption + body[endDescription:]


def update_associations(doc):
    """
    Update `associations` from `body_html` draft js state.
    When new media item is added/removed in body html,
    `associations` in update dict will be updated from body html.

    :param dict doc: update data
    """
    if not doc.get("fields_meta", {}).get("body_html") or ASSOCIATIONS not in doc:
        return
    entityMap = doc["fields_meta"]["body_html"]["draftjsState"][0].get("entityMap", {})
    associations = doc.get(ASSOCIATIONS, {})
    doc[ASSOCIATIONS] = {k: None if k.startswith(EDITOR_KEY_PREFIX) else v for k, v in associations.items()}

    mediaList = {
        EDITOR_KEY_PREFIX + key: entity["data"]["media"]
        for key, entity in entityMap.items()
        if entity.get("type", None) == "MEDIA"
    }

    doc[ASSOCIATIONS].update(mediaList)


def flush_renditions(updates, original):
    """Removes incorrect custom renditions from `updates`.

    Sometimes, when image (association) in `updates` is small, it can't fill all custom renditions,
    in this case, after merge of `updates` and `original`, custom renditions will point to old values from `original`,
    which is wrong.
    This function finds such cases and removes them.

    :param dict updates: updates for the document
    :param original: original is document
    """
    if ASSOCIATIONS not in original or ASSOCIATIONS not in updates or not updates[ASSOCIATIONS]:
        return

    default_renditions = ("original", "baseImage", "thumbnail", "viewImage")

    for key in [k for k in updates[ASSOCIATIONS] if k in original[ASSOCIATIONS]]:
        try:
            new_href = updates[ASSOCIATIONS][key]["renditions"]["original"]["href"]
            old_href = original[ASSOCIATIONS][key]["renditions"]["original"]["href"]
        except (KeyError, TypeError):
            continue
        else:
            if new_href != old_href:
                new_renditions = [r for r in updates[ASSOCIATIONS][key]["renditions"] if r not in default_renditions]
                old_renditions = [r for r in original[ASSOCIATIONS][key]["renditions"] if r not in default_renditions]
                for old_rendition in old_renditions:
                    if old_rendition not in new_renditions:
                        updates[ASSOCIATIONS][key]["renditions"][old_rendition] = None


class ArchiveVersionsResource(Resource):
    schema = item_schema()
    extra_response_fields = extra_response_fields
    item_url = item_url
    resource_methods = []
    internal_resource = True
    privileges = {"PATCH": "archive"}
    mongo_indexes = {
        "guid": ([("guid", 1)], {"background": True}),
        "_id_document_1": ([("_id_document", 1)], {"background": True}),
    }


class ArchiveVersionsService(BaseService):
    def on_deleted(self, doc):
        remove_media_files(doc)


class ArchiveResource(Resource):
    schema = item_schema()
    extra_response_fields = extra_response_fields
    item_url = item_url
    datasource = {
        "search_backend": "elastic",
        "aggregations": aggregations,
        "es_highlight": get_elastic_highlight_query,
        "projection": {"old_version": 0, "last_version": 0},
        "default_sort": [("_updated", -1)],
        "elastic_filter": {
            "bool": {
                "must": {
                    "terms": {
                        "state": [
                            "draft",
                            "fetched",
                            "routed",
                            "in_progress",
                            "spiked",
                            "submitted",
                            "unpublished",
                            "correction",
                        ]
                    }
                },
                "must_not": {"term": {"version": 0}},
            }
        },
        "elastic_filter_callback": private_content_filter,
    }
    etag_ignore_fields = ["highlights", "broadcast"]
    resource_methods = ["GET", "POST"]
    item_methods = ["GET", "PATCH", "PUT"]
    versioning = True
    privileges = {"POST": SOURCE, "PATCH": SOURCE, "PUT": SOURCE}
    mongo_indexes = {
        "processed_from_1": ([(PROCESSED_FROM, 1)], {"background": True}),
        "unique_id_1": ([("unique_id", 1)], {"background": True}),
    }


class ArchiveService(BaseService):
    packageService = PackageService()
    mediaService = ArchiveMediaService()
    cropService = CropService()

    def on_fetched(self, docs):
        """
        Overriding this to handle existing data in Mongo & Elastic
        """
        self.enhance_items(docs[config.ITEMS])

    def on_fetched_item(self, doc):
        self.enhance_items([doc])

    def enhance_items(self, items):
        for item in items:
            handle_existing_data(item)

    def on_create(self, docs):
        on_create_item(docs)

        for doc in docs:
            if doc.get("body_footer") and is_normal_package(doc):
                raise SuperdeskApiError.badRequestError(_("Package doesn't support Public Service Announcements"))

            editor_utils.generate_fields(doc)
            self._test_readonly_stage(doc)

            doc["version_creator"] = doc["original_creator"]
            remove_unwanted(doc)
            update_word_count(doc)
            set_item_expiry({}, doc)

            if doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                self.packageService.on_create([doc])

            # Do the validation after Circular Reference check passes in Package Service
            update_schedule_settings(doc, EMBARGO, doc.get(EMBARGO))
            self.validate_embargo(doc)

            update_associations(doc)
            for key, assoc in doc.get(ASSOCIATIONS, {}).items():
                # don't set time stamp for related items
                if not is_related_content(key):
                    self._set_association_timestamps(assoc, doc)
                    remove_unwanted(assoc)

            if doc.get("media"):
                self.mediaService.on_create([doc])

            # let client create version 0 docs
            if doc.get("version") == 0:
                doc[config.VERSION] = doc["version"]

            self._add_desk_metadata(doc, {})

            convert_task_attributes_to_objectId(doc)
            transtype_metadata(doc)

            if doc.get("macro"):  # if there is a macro, execute it
                get_resource_service("macros").execute_macro(doc, doc["macro"])

            # send signal
            superdesk.item_create.send(self, item=doc)

    def on_created(self, docs):
        packages = [doc for doc in docs if doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE]
        if packages:
            self.packageService.on_created(packages)

        profiles = set()
        for doc in docs:
            subject = get_subject(doc)
            if subject:
                msg = 'added new {{ type }} item about "{{ subject }}"'
            else:
                msg = "added new {{ type }} item with empty header/title"
            add_activity(ACTIVITY_CREATE, msg, self.datasource, item=doc, type=doc[ITEM_TYPE], subject=subject)

            if doc.get("profile"):
                profiles.add(doc["profile"])

            self.cropService.update_media_references(doc, {})
            if doc[ITEM_OPERATION] == ITEM_FETCH:
                app.on_archive_item_updated({"task": doc.get("task")}, doc, ITEM_FETCH)
            else:
                app.on_archive_item_updated({"task": doc.get("task")}, doc, ITEM_CREATE)

            # used by client to detect item type
            doc.setdefault("_type", "archive")

        get_resource_service("content_types").set_used(profiles)

        push_content_notification(docs)

    def on_update(self, updates, original):
        """Runs on archive update.

        Overridden to validate the updates to the article and takes necessary actions depending on the updates.
        In brief, it does the following:
            1. Sets state, item operation, version created, version creator, sign off and word count.
            2. Resets Item Expiry
            3. Creates Crops if article is a picture
        """
        user = get_user()

        editor_utils.generate_fields(updates)
        if ITEM_TYPE in updates:
            del updates[ITEM_TYPE]

        self._validate_updates(original, updates, user)

        if self.__is_req_for_save(updates):
            publish_from_personal = flask.request.args.get("publish_from_personal") if flask.request else False
            update_state(original, updates, publish_from_personal)

        remove_unwanted(updates)
        self._add_system_updates(original, updates, user)
        self._add_desk_metadata(updates, original)
        self._handle_media_updates(updates, original, user)
        flush_renditions(updates, original)
        update_refs(updates, original)

    def _handle_media_updates(self, updates, original, user):
        update_associations(updates)

        if original[ITEM_TYPE] == CONTENT_TYPE.PICTURE:  # create crops
            self.cropService.create_multiple_crops(updates, original)

        if not updates.get(ASSOCIATIONS):
            return

        body = updates.get("body_html", original.get("body_html", None))

        # iterate over associations. Validate and process them if they are stored in database
        for item_name, item_obj in updates.get(ASSOCIATIONS).items():
            if not (item_obj and config.ID_FIELD in item_obj):
                continue

            item_id = item_obj[config.ID_FIELD]
            media_item = self.find_one(req=None, _id=item_id)
            if app.settings.get("COPY_METADATA_FROM_PARENT") and item_obj.get(ITEM_TYPE) in MEDIA_TYPES:
                stored_item = (original.get(ASSOCIATIONS) or {}).get(item_name) or item_obj
            else:
                stored_item = media_item
                if not stored_item:
                    continue

            track_usage(media_item, stored_item, item_obj, item_name, original)

            if is_related_content(item_name):
                continue

            self._validate_updates(stored_item, item_obj, user)
            if stored_item[ITEM_TYPE] == CONTENT_TYPE.PICTURE:  # create crops
                CropService().create_multiple_crops(item_obj, stored_item)
                if body and item_obj.get("description_text", None):
                    body = update_image_caption(body, item_name, item_obj["description_text"])

            self._set_association_timestamps(item_obj, updates, new=False)

            stored_item.update(item_obj)

            updates[ASSOCIATIONS][item_name] = stored_item
        if body:
            updates["body_html"] = body

    def on_updated(self, updates, original):
        get_component(ItemAutosave).clear(original["_id"])

        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            self.packageService.on_updated(updates, original)

        updated = copy(original)
        updated.update(updates)

        if config.VERSION in updates:
            add_activity(
                ACTIVITY_UPDATE,
                'created new version {{ version }} for item {{ type }} about "{{ subject }}"',
                self.datasource,
                item=updated,
                version=updates[config.VERSION],
                subject=get_subject(updates, original),
                type=updated[ITEM_TYPE],
            )

        push_content_notification([updated, original])
        get_resource_service("archive_broadcast").reset_broadcast_status(updates, original)

        if updates.get("profile"):
            get_resource_service("content_types").set_used([updates.get("profile")])

        self.cropService.update_media_references(updates, original)

    def on_replace(self, document, original):
        document[ITEM_OPERATION] = ITEM_UPDATE
        remove_unwanted(document)
        user = get_user()
        lock_user = original.get("lock_user", None)
        force_unlock = document.get("force_unlock", False)
        user_id = str(user.get("_id"))
        if lock_user and str(lock_user) != user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError(_("The item was locked by another user"))
        document["versioncreated"] = utcnow()
        set_item_expiry(document, original)
        document["version_creator"] = user_id
        if force_unlock:
            del document["force_unlock"]

    def on_replaced(self, document, original):
        get_component(ItemAutosave).clear(original["_id"])
        add_activity(
            ACTIVITY_UPDATE,
            "replaced item {{ type }} about {{ subject }}",
            self.datasource,
            item=original,
            type=original["type"],
            subject=get_subject(original),
        )
        push_content_notification([document, original])
        self.cropService.update_media_references(document, original)

    def on_deleted(self, doc):
        get_component(ItemAutosave).clear(doc["_id"])
        if doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            self.packageService.on_deleted(doc)

        remove_media_files(doc)

        add_activity(
            ACTIVITY_DELETE,
            "removed item {{ type }} about {{ subject }}",
            self.datasource,
            item=doc,
            type=doc[ITEM_TYPE],
            subject=get_subject(doc),
        )
        push_expired_notification([doc.get(config.ID_FIELD)])
        app.on_archive_item_deleted(doc)

    def replace(self, id, document, original):
        return self.restore_version(id, document, original) or super().replace(id, document, original)

    def get(self, req, lookup):
        if req is None and lookup is not None and "$or" in lookup:
            # embedded resource generates mongo query which doesn't work with elastic
            # so it needs to be fixed here
            return super().get(req, lookup["$or"][0])
        return super().get(req, lookup)

    def find_one(self, req, **lookup):
        item = super().find_one(req, **lookup)

        if item and str(item.get("task", {}).get("stage", "")) in get_resource_service(
            "users"
        ).get_invisible_stages_ids(get_user().get("_id")):
            raise SuperdeskApiError.forbiddenError(_("User does not have permissions to read the item."))

        handle_existing_data(item)
        return item

    def restore_version(self, id, doc, original):
        item_id = id
        old_version = int(doc.get("old_version", 0))
        last_version = int(doc.get("last_version", 0))
        if not all([item_id, old_version, last_version]):
            return None

        old = get_resource_service("archive_versions").find_one(
            req=None, _id_document=item_id, _current_version=old_version
        )
        if old is None:
            raise SuperdeskApiError.notFoundError(_("Invalid version {old_version}").format(old_version=old_version))

        curr = get_resource_service(SOURCE).find_one(req=None, _id=item_id)
        if curr is None:
            raise SuperdeskApiError.notFoundError(_("Invalid item id {item_id}").format(item_id=item_id))

        if curr[config.VERSION] != last_version:
            raise SuperdeskApiError.preconditionFailedError(
                _("Invalid last version {last_version}").format(last_version=last_version)
            )

        old["_id"] = old["_id_document"]
        old["_updated"] = old["versioncreated"] = utcnow()
        set_item_expiry(old, doc)
        old.pop("_id_document", None)
        old.pop(SIGN_OFF, None)
        old[ITEM_OPERATION] = ITEM_RESTORE

        resolve_document_version(old, SOURCE, "PATCH", curr)
        remove_unwanted(old)
        set_sign_off(updates=old, original=curr)

        super().replace(id=item_id, document=old, original=curr)

        old.pop("old_version", None)
        old.pop("last_version", None)

        doc.update(old)
        return item_id

    def duplicate_content(self, original_doc, state=None, extra_fields=None):
        """
        Duplicates the 'original_doc' including it's version history. Copy and Duplicate actions use this method.

        :return: guid of the duplicated article
        """

        if original_doc.get(ITEM_TYPE, "") == CONTENT_TYPE.COMPOSITE:
            for groups in original_doc.get("groups"):
                if groups.get("id") != "root":
                    associations = groups.get("refs", [])
                    for assoc in associations:
                        if assoc.get(RESIDREF):
                            item, _item_id, _endpoint = self.packageService.get_associated_item(assoc)
                            assoc[RESIDREF] = assoc["guid"] = self.duplicate_content(item)

        return self.duplicate_item(original_doc, state, extra_fields)

    def duplicate_item(self, original_doc, state=None, extra_fields=None, operation=None):
        """Duplicates an item.

        Duplicates the 'original_doc' including it's version history. If the article being duplicated is contained
        in a desk then the article state is changed to Submitted.

        :return: guid of the duplicated article
        """
        new_doc = original_doc.copy()

        self.remove_after_copy(new_doc, extra_fields, delete_keys=["marked_for_user"])
        on_duplicate_item(new_doc, original_doc, operation)
        resolve_document_version(new_doc, SOURCE, "PATCH", new_doc)

        if original_doc.get("task", {}).get("desk") is not None and new_doc.get(ITEM_STATE) != CONTENT_STATE.SUBMITTED:
            new_doc[ITEM_STATE] = CONTENT_STATE.SUBMITTED

        if state:
            new_doc[ITEM_STATE] = state

        convert_task_attributes_to_objectId(new_doc)
        transtype_metadata(new_doc)
        signals.item_duplicate.send(self, item=new_doc, original=original_doc, operation=operation)
        get_model(ItemModel).create([new_doc])
        self._duplicate_versions(original_doc["_id"], new_doc)
        self._duplicate_history(original_doc["_id"], new_doc)
        app.on_archive_item_updated({"duplicate_id": new_doc["guid"]}, original_doc, operation or ITEM_DUPLICATE)

        if original_doc.get("task"):
            # Store the new task details along with this history entry
            app.on_archive_item_updated(
                {"duplicate_id": original_doc["_id"], "task": original_doc.get("task")},
                new_doc,
                operation or ITEM_DUPLICATED_FROM,
            )
        else:
            app.on_archive_item_updated(
                {"duplicate_id": original_doc["_id"]}, new_doc, operation or ITEM_DUPLICATED_FROM
            )

        signals.item_duplicated.send(self, item=new_doc, original=original_doc, operation=operation)

        return new_doc["guid"]

    def remove_after_copy(self, copied_item, extra_fields=None, delete_keys=None):
        """Removes the properties which doesn't make sense to have for an item after copy.

        :param copied_item: item to copy
        :param extra_fields: extra fields to copy besides content fields
        """
        # get the archive schema keys
        archive_schema_keys = list(app.config["DOMAIN"][SOURCE]["schema"].keys())
        archive_schema_keys.extend(
            [config.ID_FIELD, config.LAST_UPDATED, config.DATE_CREATED, config.VERSION, config.ETAG]
        )

        # Delete the keys that are not part of archive schema.
        keys_to_delete = [key for key in copied_item.keys() if key not in archive_schema_keys]
        keys_to_delete.extend(
            [
                config.ID_FIELD,
                "guid",
                LINKED_IN_PACKAGES,
                EMBARGO,
                PUBLISH_SCHEDULE,
                SCHEDULE_SETTINGS,
                "lock_time",
                "lock_action",
                "lock_session",
                "lock_user",
                SIGN_OFF,
                "rewritten_by",
                "rewrite_of",
                "rewrite_sequence",
                "highlights",
                "marked_desks",
                "_type",
                "event_id",
                "assignment_id",
                PROCESSED_FROM,
                "translations",
                "translation_id",
                "translated_from",
                "firstpublished",
            ]
        )
        if delete_keys:
            keys_to_delete.extend(delete_keys)

        if extra_fields:
            keys_to_delete = [key for key in keys_to_delete if key not in extra_fields]

        for key in keys_to_delete:
            copied_item.pop(key, None)

        # Copy should not preseve the SMS flag
        if copied_item.get("flags", {}).get("marked_for_sms", False):
            copied_item["flags"]["marked_for_sms"] = False

        task = copied_item.get("task", {})
        task.pop(LAST_PRODUCTION_DESK, None)
        task.pop(LAST_AUTHORING_DESK, None)

    def _duplicate_versions(self, old_id, new_doc):
        """Duplicates versions for an item.

        Duplicates the versions of the article identified by old_id. Each version identifiers are changed
        to have the identifiers of new_doc.

        :param old_id: identifier to fetch versions
        :param new_doc: identifiers from this doc will be used to create versions for the duplicated item.
        """
        resource_def = app.config["DOMAIN"]["archive"]
        version_id = versioned_id_field(resource_def)
        old_versions = get_resource_service("archive_versions").get(req=None, lookup={version_id: old_id})

        new_versions = []
        for old_version in old_versions:
            old_version[version_id] = new_doc[config.ID_FIELD]
            del old_version[config.ID_FIELD]

            old_version["guid"] = new_doc["guid"]
            old_version["unique_name"] = new_doc["unique_name"]
            old_version["unique_id"] = new_doc["unique_id"]
            old_version["versioncreated"] = utcnow()
            if old_version[config.VERSION] == new_doc[config.VERSION]:
                old_version[ITEM_OPERATION] = new_doc[ITEM_OPERATION]
            new_versions.append(old_version)

        last_version = deepcopy(new_doc)
        last_version["_id_document"] = new_doc["_id"]
        del last_version["_id"]
        new_versions.append(last_version)
        if new_versions:
            get_resource_service("archive_versions").post(new_versions)

    def _duplicate_history(self, old_id, new_doc):
        """Duplicates history for an item.

        Duplicates the history of the article identified by old_id. Each history identifiers are changed
        to have the identifiers of new_doc.

        :param old_id: identifier to fetch history
        :param new_doc: identifiers from this doc will be used to create version history for the duplicated item.
        """
        old_history_items = get_resource_service("archive_history").get(req=None, lookup={"item_id": old_id})

        new_history_items = []
        for old_history_item in old_history_items:
            del old_history_item[config.ID_FIELD]
            old_history_item["item_id"] = new_doc["guid"]
            if not old_history_item.get("original_item_id"):
                old_history_item["original_item_id"] = old_id

            new_history_items.append(old_history_item)

        if new_history_items:
            get_resource_service("archive_history").post(new_history_items)

    def update(self, id, updates, original):
        if updates.get(ASSOCIATIONS):
            for key, association in updates[ASSOCIATIONS].items():
                if association is None:
                    continue
                # don't set time stamp for related items
                if not is_related_content(key):
                    self._set_association_timestamps(association, updates, new=False)
                    remove_unwanted(association)

        # this needs to here as resolve_nested_documents (in eve) will add the schedule_settings
        if PUBLISH_SCHEDULE in updates and original[ITEM_STATE] == CONTENT_STATE.SCHEDULED:
            self.deschedule_item(updates, original)  # this is an deschedule action

        # send signal
        signals.item_update.send(self, updates=updates, original=original)

        super().update(id, updates, original)

        updated = copy(original)
        updated.update(updates)
        signals.item_updated.send(self, item=updated, original=original)

        if "marked_for_user" in updates:
            self.handle_mark_user_notifications(updates, original)

    def deschedule_item(self, updates, original):
        """Deschedule an item.

        This operation removed the item from publish queue and published collection.
        :param dict updates: updates for the document
        :param original: original is document.
        """
        updates[ITEM_STATE] = CONTENT_STATE.PROGRESS
        updates[PUBLISH_SCHEDULE] = original[PUBLISH_SCHEDULE]
        updates[SCHEDULE_SETTINGS] = original[SCHEDULE_SETTINGS]
        updates[ITEM_OPERATION] = ITEM_DESCHEDULE
        updates["firstpublished"] = None
        # delete entry from published repo
        get_resource_service("published").delete_by_article_id(original["_id"])

        # deschedule scheduled associations
        if config.PUBLISH_ASSOCIATED_ITEMS:
            associations = original.get(ASSOCIATIONS) or {}
            archive_service = get_resource_service("archive")
            for associations_key, associated_item in associations.items():
                if not associated_item:
                    continue
                orig_associated_item = archive_service.find_one(req=None, _id=associated_item[config.ID_FIELD])
                if orig_associated_item and orig_associated_item.get("state") == CONTENT_STATE.SCHEDULED:
                    # deschedule associated item itself
                    archive_service.patch(id=associated_item[config.ID_FIELD], updates={PUBLISH_SCHEDULE: None})
                    # update associated item info in the original
                    orig_associated_item = archive_service.find_one(req=None, _id=associated_item[config.ID_FIELD])
                    updates.setdefault(ASSOCIATIONS, {})[associations_key] = orig_associated_item

    def can_edit(self, item, user_id):
        """
        Determines if the user can edit the item or not.
        """
        # TODO: modify this function when read only permissions for stages are implemented
        # TODO: and Content state related checking.

        if not current_user_has_privilege("archive"):
            return False, "User does not have sufficient permissions."

        item_location = item.get("task")

        if item_location:
            if item_location.get("desk"):
                if not superdesk.get_resource_service("user_desks").is_member(user_id, item_location.get("desk")):
                    return False, "User is not a member of the desk."
            elif item_location.get("user"):
                if not str(item_location.get("user")) == str(user_id):
                    return False, "Item belongs to another user."

        return True, ""

    def delete_by_article_ids(self, ids):
        """Remove the content

        :param list ids: list of ids to be removed
        """
        version_field = versioned_id_field(app.config["DOMAIN"]["archive_versions"])
        get_resource_service("archive_versions").delete_action(lookup={version_field: {"$in": ids}})
        super().delete_action({config.ID_FIELD: {"$in": ids}})

    def _set_association_timestamps(self, assoc_item, updates, new=True):
        if type(assoc_item) == dict:
            assoc_item[config.LAST_UPDATED] = updates.get(config.LAST_UPDATED, datetime.datetime.now())
            if new:
                assoc_item[config.DATE_CREATED] = datetime.datetime.now()
            elif config.DATE_CREATED in assoc_item:
                del assoc_item[config.DATE_CREATED]

    def __is_req_for_save(self, doc):
        """Checks if doc contains req_for_save key.

        Patch of /api/archive is being used in multiple places. This method differentiates from the patch
        triggered by user or not.

        :param dictionary doc: doc to test
        """

        if "req_for_save" in doc:
            req_for_save = doc["req_for_save"]
            del doc["req_for_save"]

            return req_for_save == "true"

        return True

    def validate_embargo(self, item):
        """Validates the embargo of the item.

        Following are checked:
            1. Item can't be a package or a re-write of another story
            2. Publish Schedule and Embargo are mutually exclusive
            3. Always a future date except in case of Corrected and Killed.
        :raises: SuperdeskApiError.badRequestError() if the validation fails
        """

        if item[ITEM_TYPE] != CONTENT_TYPE.COMPOSITE:
            if EMBARGO in item:
                embargo = item.get(SCHEDULE_SETTINGS, {}).get("utc_{}".format(EMBARGO))
                if embargo:
                    if item.get(PUBLISH_SCHEDULE) or item[ITEM_STATE] == CONTENT_STATE.SCHEDULED:
                        raise SuperdeskApiError.badRequestError(
                            _("An item can't have both Publish Schedule and Embargo")
                        )

                    if (
                        item[ITEM_STATE] not in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED, CONTENT_STATE.SCHEDULED}
                    ) and embargo <= utcnow():
                        raise SuperdeskApiError.badRequestError(_("Embargo cannot be earlier than now"))

                    if item.get("rewrite_of"):
                        raise SuperdeskApiError.badRequestError(_("Rewrites doesn't support Embargo"))

                    if not isinstance(embargo, datetime.date) or not embargo.time():
                        raise SuperdeskApiError.badRequestError(_("Invalid Embargo"))

        elif is_normal_package(item):
            if item.get(EMBARGO):
                raise SuperdeskApiError.badRequestError(_("A Package doesn't support Embargo"))

            self.packageService.check_if_any_item_in_package_has_embargo(item)

    def _test_readonly_stage(self, item, updates=None):
        """If item is created or updated on readonly stage abort it.

        :param item: edited/new item
        :param updates: item updates
        """

        def abort_if_readonly_stage(stage_id):
            stage = superdesk.get_resource_service("stages").find_one(req=None, _id=stage_id)
            if stage.get("local_readonly"):
                flask.abort(403, response={"readonly": True})

        orig_stage_id = item.get("task", {}).get("stage")
        if orig_stage_id and get_user() and not item.get(INGEST_ID):
            abort_if_readonly_stage(orig_stage_id)

        if updates:
            dest_stage_id = updates.get("task", {}).get("stage")
            if dest_stage_id and get_user() and not item.get(INGEST_ID):
                abort_if_readonly_stage(dest_stage_id)

    def _validate_updates(self, original, updates, user):
        """Validates updates to the article for the below conditions.

        If any of these conditions are met then exception is raised:
            1.  Is article locked by another user other than the user requesting for update
            2.  Is state of the article is Killed or Recalled?
            3.  Is user trying to update the package with Public Service Announcements?
            4.  Is user authorized to update unique name of the article?
            5.  Is user trying to update the genre of a broadcast article?
            6.  Is article being scheduled and is in a package?
            7.  Is article being scheduled and schedule timestamp is invalid?
            8.  Does article has valid crops if the article type is a picture?
            9.  Is article a valid package if the article type is a package?
            10. Does article has a valid Embargo?
            11. Make sure that there are no duplicate anpa_category codes in the article.
            12. Make sure there are no duplicate subjects in the upadte
            13. Item is on readonly stage.

        :raises:
            SuperdeskApiError.forbiddenError()
                - if state of the article is killed or user is not authorized to update unique name or if article is
                  locked by another user
            SuperdeskApiError.badRequestError()
                - if Public Service Announcements are being added to a package or genre is being updated for a
                broadcast, is invalid for scheduling, the updates contain duplicate anpa_category or subject codes
        """
        updated = original.copy()
        updated.update(updates)

        self._test_readonly_stage(original, updates)

        lock_user = original.get("lock_user", None)
        force_unlock = updates.get("force_unlock", False)
        str_user_id = str(user.get(config.ID_FIELD)) if user else None

        if lock_user and str(lock_user) != str_user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError(_("The item was locked by another user"))

        if original.get(ITEM_STATE) in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED}:
            raise SuperdeskApiError.forbiddenError(_("Item isn't in a valid state to be updated."))

        if updates.get("body_footer") and is_normal_package(original):
            raise SuperdeskApiError.badRequestError(_("Package doesn't support Public Service Announcements"))

        if (
            "unique_name" in updates
            and not is_admin(user)
            and (user["active_privileges"].get("metadata_uniquename", 0) == 0)
            and not force_unlock
        ):
            raise SuperdeskApiError.forbiddenError(_("Unauthorized to modify Unique Name"))

        # if broadcast then update to genre is not allowed.
        if (
            original.get("broadcast")
            and updates.get("genre")
            and any(genre.get("qcode", "").lower() != BROADCAST_GENRE.lower() for genre in updates.get("genre"))
        ):
            raise SuperdeskApiError.badRequestError(_("Cannot change the genre for broadcast content."))

        if (PUBLISH_SCHEDULE in updates or "schedule_settings" in updates) and original.get(
            "state"
        ) != CONTENT_STATE.PUBLISHED:
            if (
                (
                    updates.get(PUBLISH_SCHEDULE, None)
                    or any(v is not None for v in updates.get("schedule_settings", {}).values())
                )
                and is_item_in_package(original)
                and not force_unlock
            ):
                raise SuperdeskApiError.badRequestError(
                    _("This item is in a package and it needs to be removed before the item can be scheduled!")
                )

            update_schedule_settings(updated, PUBLISH_SCHEDULE, updated.get(PUBLISH_SCHEDULE))

            if updates.get(PUBLISH_SCHEDULE) and updates.get("state") != CONTENT_STATE.PUBLISHED:
                validate_schedule(updated.get(SCHEDULE_SETTINGS, {}).get("utc_{}".format(PUBLISH_SCHEDULE)))

            updates[SCHEDULE_SETTINGS] = updated.get(SCHEDULE_SETTINGS, {})

        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            self.packageService.on_update(updates, original)

        if original[ITEM_TYPE] == CONTENT_TYPE.PICTURE and not force_unlock:
            CropService().validate_multiple_crops(updates, original)

        # update the embargo date
        update_schedule_settings(updated, EMBARGO, updated.get(EMBARGO))
        # Do the validation after Circular Reference check passes in Package Service
        if not force_unlock:
            self.validate_embargo(updated)
        if EMBARGO in updates or "schedule_settings" in updates:
            updates[SCHEDULE_SETTINGS] = updated.get(SCHEDULE_SETTINGS, {})

        # Ensure that there are no duplicate categories in the update
        category_qcodes = [q["qcode"] for q in updates.get("anpa_category", []) or []]
        if category_qcodes and len(category_qcodes) != len(set(category_qcodes)):
            raise SuperdeskApiError.badRequestError(_("Duplicate category codes are not allowed"))

        # Ensure that there are no duplicate subjects in the update
        subject_qcodes = [format_subj_qcode(q) for q in updates.get("subject", []) or []]
        if subject_qcodes and len(subject_qcodes) != len(set(subject_qcodes)):
            raise SuperdeskApiError.badRequestError(_("Duplicate subjects are not allowed"))

    def _add_system_updates(self, original, updates, user):
        """Adds system updates to item.

        As the name suggests, this method adds properties which are derived based on updates sent in the request.
            1. Sets item operation, version created, version creator, sign off and word count.
            2. Resets Item Expiry
        """

        convert_task_attributes_to_objectId(updates)
        transtype_metadata(updates, original)

        updates[ITEM_OPERATION] = ITEM_UPDATE
        updates.setdefault("original_creator", original.get("original_creator"))
        updates["versioncreated"] = utcnow()
        updates["version_creator"] = str(user.get(config.ID_FIELD)) if user else None

        update_word_count(updates, original)
        update_version(updates, original)

        set_item_expiry(updates, original)
        set_sign_off(updates, original=original)
        set_dateline(updates, original)

        # Clear publish_schedule field
        if (
            updates.get(PUBLISH_SCHEDULE)
            and datetime.datetime.fromtimestamp(0).date() == updates.get(PUBLISH_SCHEDULE).date()
        ):
            updates[PUBLISH_SCHEDULE] = None
            updates[SCHEDULE_SETTINGS] = {}

        if updates.get("force_unlock", False):
            del updates["force_unlock"]

    def get_expired_items(self, expiry_datetime, invalid_only=False):
        """Get the expired items.

        Where content state is not scheduled and the item matches given parameters

        :param datetime expiry_datetime: expiry datetime
        :param bool invalid_only: True only invalid items
        :return pymongo.cursor: expired non published items.
        """
        unique_id = 0

        while True:
            req = ParsedRequest()
            req.sort = "unique_id"
            query = {
                "$and": [
                    {"expiry": {"$lte": date_to_str(expiry_datetime)}},
                    {"$or": [{"task.desk": {"$ne": None}}, {ITEM_STATE: CONTENT_STATE.SPIKED, "task.desk": None}]},
                ]
            }

            query["$and"].append({"unique_id": {"$gt": unique_id}})

            if invalid_only:
                query["$and"].append({"expiry_status": "invalid"})
            else:
                query["$and"].append({"expiry_status": {"$ne": "invalid"}})

            req.where = json.dumps(query)

            req.max_results = config.MAX_EXPIRY_QUERY_LIMIT
            items = list(self.get_from_mongo(req=req, lookup=None))

            if not len(items):
                break

            unique_id = items[-1]["unique_id"]
            yield items

    def _add_desk_metadata(self, updates, original):
        """Populate updates metadata from item desk in case it's set.

        It will only add data which is not set yet on the item.

        :param updates: updates to item that should be saved
        :param original: original item version before update
        """
        return get_resource_service("desks").apply_desk_metadata(updates, original)

    def handle_mark_user_notifications(self, updates, original, add_activity=True):
        """Notify user when item is marked or unmarked

        :param updates: updates to item that should be saved
        :param original: original item version before update
        :param add_activity: flag to decide whether to add notification as activity or not
        """
        marked_user = marked_for_user = None
        orig_marked_user = original.get("marked_for_user", None)
        new_marked_user = updates.get("marked_for_user", None)
        by_user = get_user().get("display_name", get_user().get("username"))
        user_service = get_resource_service("users")

        if new_marked_user:
            marked_user = user_service.find_one(req=None, _id=new_marked_user)
            marked_for_user = marked_user.get("display_name", marked_user.get("username"))

        if orig_marked_user and not new_marked_user:
            # sent when unmarking user from item
            user_list = [user_service.find_one(req=None, _id=orig_marked_user)]
            message = 'Item "{headline}" has been unmarked by {by_user}.'.format(
                headline=original.get("headline", original.get("slugline", "item")), by_user=by_user
            )

            self._send_mark_user_notifications(
                "item:unmarked",
                message,
                resource=self.datasource,
                item=original,
                user_list=user_list,
                add_activity=add_activity,
            )
        elif marked_user and marked_for_user:
            # sent when mark item for user or mark to another user
            user_list = [marked_user]
            if new_marked_user and orig_marked_user and new_marked_user != orig_marked_user:
                user_list.append(user_service.find_one(req=None, _id=orig_marked_user))

            message = 'Item "{headline}" has been marked for {for_user} by {by_user}.'.format(
                headline=original.get("headline", original.get("slugline", "item")),
                for_user=marked_for_user,
                by_user=by_user,
            )

            self._send_mark_user_notifications(
                "item:marked",
                message,
                resource=self.datasource,
                item=original,
                user_list=user_list,
                add_activity=add_activity,
                marked_for_user=marked_for_user,
            )

    def _send_mark_user_notifications(
        self, activity_name, msg, resource=None, item=None, user_list=None, add_activity=True, **data
    ):
        """Send notifications on mark or unmark user operation

        :param activity_name: Name of the activity
        :param msg: Notification message to be sent
        :param resource: resource name generating this notification
        :param item: marked or unmarked article, default None
        :param user_list: users to be notified
        :param add_activity: flag to decide whether to add notification as activity or not
        :param data: kwargs
        """

        if item.get("type") == "text":
            link_id = item.get("guid", item.get("_id"))
        else:
            # since guid and _id do not match for the item of type picture, audio and video
            # create link using _id instead of guid for media items
            # and item_id for published media items as _id or guid does not match _id in archive for media items
            link_id = item.get("item_id") if item.get("state") in PUBLISH_STATES else item.get("_id")

        client_url = app.config.get("CLIENT_URL", "").rstrip("/")
        link = "{}/#/workspace?item={}&action=view".format(client_url, link_id)

        if add_activity:
            notify_and_add_activity(
                activity_name, msg, resource=resource, item=item, user_list=user_list, link=link, **data
            )
        # send separate notification for markForUser extension
        push_notification(
            activity_name, item_id=item.get(config.ID_FIELD), user_list=user_list, extension="markForUser"
        )

    def get_items_chain(self, item):
        """
        Get the whole items chain which includes all previous updates,
        all translations and the original item.

        Result list may contain:
            - original item
            - original item's translations
            - update-1 item
            - update-1 item's translations
            - update-N item
            - update-N item's translations
            - `item`
            - `item`'s translations
        NOTE: The first item in the list is the original item

        :param item: item can be an "initial", "rewrite", or "translation"
        :type item: dict
        :return: chain of items
        :rtype: list
        """

        def get_item_translated_from(item):
            _item = item
            for _i in range(50):
                try:
                    item = self.find_one(req={}, _id=item["translated_from"])
                except Exception:
                    break
            else:
                logger.error(
                    "Failed to retrive an initial item from which item {} was translated from".format(_item.get("_id"))
                )
            return item

        item = get_item_translated_from(item)
        # add item + translations
        items_chain = [item]
        items_chain += self.get_item_translations(item)

        for _i in range(50):
            try:
                item = self.find_one(req={}, _id=item["rewrite_of"])
                # prepend translations + update
                items_chain = [item, *self.get_item_translations(item), *items_chain]
            except Exception:
                # `item` is not an update, but it can be a translation
                if "translated_from" in item:
                    translation_item = item
                    item = get_item_translated_from(item)
                    # add item + translations
                    items_chain = [
                        item,
                        *[
                            i
                            for i in self.get_item_translations(item)
                            # `translation_item` was already added into `items_chain` on a previous iteration
                            if i["_id"] != translation_item["_id"]
                        ],
                        *items_chain,
                    ]
                else:
                    # `item` is not a translation and not an update, it means that it's an initial
                    break

        else:
            logger.error("Failed to retrieve the whole items chain for item {}".format(item.get("_id")))
        return items_chain

    def get_item_translations(self, item):
        """
        Get list of item's translations.
        :param item: item
        :type item: dict
        :return: list of dicts
        :rtype: list
        """
        translation_items = []

        for translation_item_id in item.get("translations", []):
            translation_item = self.find_one(req={}, _id=translation_item_id)
            translation_items.append(translation_item)
            # get a translation of a translation and so on
            translation_items += self.get_item_translations(translation_item)

        return translation_items


class AutoSaveResource(Resource):
    endpoint_name = "archive_autosave"
    item_url = item_url
    schema = get_schema(versioning=True)
    resource_methods = ["POST"]
    item_methods = ["GET", "PUT", "PATCH", "DELETE"]
    resource_title = endpoint_name
    privileges = {"POST": "archive", "PATCH": "archive", "PUT": "archive", "DELETE": "archive"}


class ArchiveSaveService(BaseService):
    def create(self, docs, **kwargs):
        if not docs:
            raise SuperdeskApiError.notFoundError("Content is missing")

        for doc in docs:
            editor_utils.generate_fields(doc)

        req = parse_request(self.datasource)
        try:
            get_component(ItemAutosave).autosave(docs[0]["_id"], docs[0], get_user(required=True), req.if_match)
        except InvalidEtag:
            raise SuperdeskApiError.preconditionFailedError(_("Client and server etags don't match"))
        except KeyError:
            raise SuperdeskApiError.badRequestError(_("Request for Auto-save must have _id"))
        return [docs[0]["_id"]]

    def on_fetched_item(self, item):
        item["_type"] = "archive"
        return item


superdesk.workflow_state("in_progress")
superdesk.workflow_action(
    name="save",
    include_states=["draft", "fetched", "routed", "submitted", "scheduled", "unpublished"],
    privileges=["archive"],
)

superdesk.workflow_state("submitted")
superdesk.workflow_action(
    name="move",
    exclude_states=["ingested", "spiked", "on-hold", "published", "scheduled", "killed"],
    privileges=["archive"],
)

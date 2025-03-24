# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import logging
import datetime
from copy import copy, deepcopy
from typing import Dict, List, Any, Optional, Sequence, Union, Tuple

from bson import ObjectId

import superdesk
import superdesk.signals as signals
from apps.archive.archive_media import ArchiveMediaService
from apps.archive.common import (
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
from apps.archive.highlights_search_mixin import HighlightsSearchMixin
from apps.common.components.utils import get_component
from apps.common.models.base_model import InvalidEtag
from apps.content import push_content_notification, push_expired_notification, push_notification
from apps.item_autosave.components.item_autosave import ItemAutosave
from apps.item_lock.models.item import ItemModel
from apps.packages import PackageService
from quart_babel import gettext as _
from superdesk import editor_utils, get_resource_service
from superdesk.activity import add_activity, notify_and_add_activity, ACTIVITY_CREATE, ACTIVITY_UPDATE, ACTIVITY_DELETE
from superdesk.core.resources.search import SearchRequest
from superdesk.core.resources.service import AsyncResourceService
from superdesk.errors import SuperdeskApiError
from superdesk.flask import request, abort
from superdesk.media.crop import CropService
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
from superdesk.metadata.utils import (
    is_normal_package,
    is_normal_package_async,
    aggregations,
    get_elastic_highlight_query,
)
from superdesk.privilege import GLOBAL_SEARCH_PRIVILEGE
from superdesk.resource_fields import ITEMS, ID_FIELD, VERSION, LAST_UPDATED, DATE_CREATED, ETAG
from superdesk.text_utils import update_word_count
from superdesk.types.archive import ArchiveResourceModel, ContentTypes, ItemOperation
from superdesk.users.services import current_user_has_privilege, is_admin
from superdesk.utc import utcnow
from superdesk.vocabularies import is_related_content
from eve.versioning import resolve_document_version, versioned_id_field

EDITOR_KEY_PREFIX = "editor_"
logger = logging.getLogger(__name__)


def format_subj_qcode(subj):
    return ":".join([code for code in [subj.get("scheme"), subj.get("qcode")] if code])


def update_image_caption(body, name, caption):
    """Update image caption in body HTML.

    :param body: HTML body content
    :param name: image name
    :param caption: new caption text
    :return: updated HTML body
    """
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
    """Update `associations` from `body_html` draft js state.

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


def remove_is_queued(item):
    """Remove is_queued flag from associated items.

    :param item: The item to process
    """
    if superdesk.get_app_config("PUBLISH_ASSOCIATED_ITEMS"):
        associations = item.get("associations") or {}
        for associations_key, associated_item in associations.items():
            if not associated_item:
                continue
            if associated_item.get("is_queued"):
                associated_item["is_queued"] = None


class AsyncArchiveService(AsyncResourceService[ArchiveResourceModel], HighlightsSearchMixin):
    """Asynchronous Archive service.

    Handles operations related to archive items.
    """

    resource_name = "archive"
    packageService = PackageService()
    mediaService = ArchiveMediaService()
    cropService = CropService()

    def enhance_items(self, items) -> None:
        """Enhance items with additional data.

        :param items: List of items to enhance
        """
        for item in items:
            handle_existing_data(item)

    async def on_create(self, docs: list[ArchiveResourceModel]) -> None:
        """Runs on archive item creation.

        :param docs: List of items to create
        """
        await on_create_item(docs, media_service=self.mediaService)

        for doc in docs:
            if doc.body_footer and await is_normal_package_async(doc):
                raise SuperdeskApiError.badRequestError(_("Package doesn't support Public Service Announcements"))

            editor_utils.generate_fields(doc)
            await self._test_readonly_stage(doc)

            doc.version_creator = doc.original_creator or None  # avoid ""
            remove_unwanted(doc)
            update_word_count(doc)
            set_item_expiry({}, doc)

            if doc.item_type == ContentTypes.COMPOSITE:
                await self.packageService.on_create([doc])

            # Do the validation after Circular Reference check passes in Package Service
            update_schedule_settings(doc, EMBARGO, doc.embargo)
            await self.validate_embargo(doc)

            update_associations(doc)
            for key, assoc in doc.associations or {}.items():
                # don't set time stamp for related items
                if not is_related_content(key):
                    self._set_association_timestamps(assoc, doc)
                    remove_unwanted(assoc)

            if doc.type:
                doc.profile = doc.profile or doc.type

            # let client create version 0 docs
            if getattr(doc, "version", None) == 0:
                doc.version = doc.version

            convert_task_attributes_to_objectId(doc)
            transtype_metadata(doc)

            if doc.macro:  # if there is a macro, execute it
                await get_resource_service("macros").execute_macro(doc, doc.macro)

            # send signal
            signals.item_create.send(self, item=doc)

    async def on_created(self, docs: list[ArchiveResourceModel]) -> None:
        """Runs after archive item creation.

        :param docs: List of created items
        """
        packages = [doc for doc in docs if doc.item_type == ContentTypes.COMPOSITE]
        if packages:
            await self.packageService.on_created(packages)

        app = superdesk.get_current_app().as_any()
        profiles = set()
        for doc in docs:
            subject = get_subject(doc)
            if subject:
                msg = 'added new {{ type }} item about "{{ subject }}"'
            else:
                msg = "added new {{ type }} item with empty header/title"
            add_activity(ACTIVITY_CREATE, msg, self.resource_name, item=doc, type=doc.item_type, subject=subject)

            if doc.profile:
                profiles.add(doc.profile)

            await self.cropService.update_media_references(doc, {})
            if doc.operation == ItemOperation.FETCH:
                await app.on_archive_item_updated({"task": doc.task}, doc, ItemOperation.FETCH)
            else:
                await app.on_archive_item_updated({"task": doc.task}, doc, ItemOperation.CREATE)

            # used by client to detect item type
            doc._type = "archive"

        await get_resource_service("content_types").set_used(profiles)

        push_content_notification(docs)

    def set_marked_for_sign_off(self, updates):
        """Set marked for sign off in updates.

        :param updates: Updates dictionary
        """
        if "marked_for_user" in updates:
            sign_off = None
            if updates["marked_for_user"]:
                user_doc = get_resource_service("users").find_one(req=None, _id=updates["marked_for_user"])
                sign_off = user_doc.get("sign_off")
            updates["marked_for_sign_off"] = sign_off

    async def on_update(self, updates: Dict[str, Any], original: ArchiveResourceModel) -> None:
        """Runs on archive update.

        Validates the updates to the article and takes necessary actions depending on the updates.

        :param updates: Updates dictionary to be applied
        :param original: Original item being updated
        """
        user = get_user()

        editor_utils.generate_fields(updates, original=original)
        if ITEM_TYPE in updates:
            del updates[ITEM_TYPE]

        # set marked for sign off key if mark for user is exists in updates
        self.set_marked_for_sign_off(updates)

        await self._validate_updates(original, updates, user)

        if self.__is_req_for_save(updates):
            publish_from_personal = request.args.get("publish_from_personal") if request else False
            update_state(original, updates, publish_from_personal)

        remove_unwanted(updates)
        self._add_system_updates(original, updates, user)
        await self._handle_media_updates(updates, original, user)
        await self._handle_attachment_updates(updates, original)
        flush_renditions(updates, original)
        await update_refs(updates, original)

    async def _handle_media_updates(self, updates: Dict[str, Any], original: ArchiveResourceModel, user):
        """Handle media updates in the item.

        :param updates: Updates dictionary
        :param original: Original item
        :param user: Current user
        """
        update_associations(updates)

        if original.item_type == ContentTypes.PICTURE:  # create crops
            await self.cropService.create_multiple_crops(updates, original)

        if not updates.get(ASSOCIATIONS):
            return

        body = updates.get("body_html", original.get("body_html", None))

        # iterate over associations. Validate and process them if they are stored in database
        for item_name, item_obj in updates.get(ASSOCIATIONS).items():
            if not (item_obj and ID_FIELD in item_obj):
                continue

            item_id = item_obj[ID_FIELD]
            media_item = await self.find_one(req=None, _id=item_id)
            parent = (original.get(ASSOCIATIONS) or {}).get(item_name) or item_obj
            if (
                superdesk.get_app_config("COPY_METADATA_FROM_PARENT")
                and item_obj.get(ITEM_TYPE) in MEDIA_TYPES
                and item_id == parent.get(ID_FIELD)
            ):
                stored_item = parent
            else:
                stored_item = media_item
                if not stored_item:
                    continue

            await track_usage(media_item, stored_item, item_obj, item_name, original)

            if is_related_content(item_name):
                continue

            await self._validate_updates(stored_item, item_obj, user)
            if stored_item[ITEM_TYPE] == CONTENT_TYPE.PICTURE:  # create crops
                await CropService().create_multiple_crops(item_obj, stored_item)
                if body and item_obj.get("description_text", None):
                    body = update_image_caption(body, item_name, item_obj["description_text"])

            self._set_association_timestamps(item_obj, updates, new=False)

            stored_item.update(item_obj)

            updates[ASSOCIATIONS][item_name] = stored_item
        if body:
            updates["body_html"] = body

    async def _handle_attachment_updates(self, updates: Dict[str, Any], original: ArchiveResourceModel) -> None:
        """Handle changes to item attachments.

        If an attachment was removed in this update, then remove the
        associated Attachment document from the collection as well

        :param updates: Updates to be applied
        :param original: Original item
        """
        if "attachments" not in updates or not len(original.get("attachments") or []):
            # No need to proceed if:
            #   - ``attachments`` is not supplied in updates, or
            #   - original has no ``attachments``
            return

        updated_attachment_ids = [attachment["attachment"] for attachment in updates["attachments"] or []]
        attachment_ids_to_remove = [
            attachment["attachment"]
            for attachment in original["attachments"]
            if attachment["attachment"] not in updated_attachment_ids
        ]

        for attachment_id in attachment_ids_to_remove:
            lookup = {"_id": attachment_id}
            await get_resource_service("attachments").delete_action(lookup)

    async def on_updated(self, updates: Dict[str, Any], original: ArchiveResourceModel) -> None:
        """Run after an item has been updated.

        :param updates: Updates that were applied
        :param original: Original item before update
        """
        get_component(ItemAutosave).clear(original.id)

        if original.item_type == ContentTypes.COMPOSITE:
            await self.packageService.on_updated(updates, original)

        updated = copy(original)
        for k, v in updates.items():
            setattr(updated, k, v)

        if VERSION in updates:
            add_activity(
                ACTIVITY_UPDATE,
                'created new version {{ version }} for item {{ type }} about "{{ subject }}"',
                self.resource_name,
                item=updated,
                version=updates[VERSION],
                subject=get_subject(updates, original),
                type=updated.item_type,
            )

        push_content_notification([updated, original])
        await get_resource_service("archive_broadcast").reset_broadcast_status(updates, original)

        if updates.get("profile"):
            await get_resource_service("content_types").set_used([updates.get("profile")])

        await self.cropService.update_media_references(updates, original)

    async def on_replace(self, document, original):
        """Run when an item is replaced.

        :param document: New document
        :param original: Original document
        """
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

    async def on_replaced(self, document, original):
        """Run after an item has been replaced.

        :param document: New document that replaced original
        :param original: Original document that was replaced
        """
        get_component(ItemAutosave).clear(original["_id"])
        add_activity(
            ACTIVITY_UPDATE,
            "replaced item {{ type }} about {{ subject }}",
            self.resource_name,
            item=original,
            type=original["type"],
            subject=get_subject(original),
        )
        push_content_notification([document, original])
        await self.cropService.update_media_references(document, original)

    async def on_deleted(self, doc):
        """Run when an item is deleted.

        :param doc: Document being deleted
        """
        get_component(ItemAutosave).clear(doc["_id"])
        if doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            await self.packageService.on_deleted(doc)

        await remove_media_files(doc, published=False)
        await self._remove_from_translations(doc)

        add_activity(
            ACTIVITY_DELETE,
            "removed item {{ type }} about {{ subject }}",
            self.resource_name,
            item=doc,
            type=doc[ITEM_TYPE],
            subject=get_subject(doc),
        )
        push_expired_notification([doc.get(ID_FIELD)])

        app = superdesk.get_current_app().as_any()
        await app.on_archive_item_deleted(doc)

    async def replace(self, id, document, original):
        """Replace the item with given document.

        :param id: ID of the item
        :param document: New document
        :param original: Original document
        :return: Result of restore_version or super().replace
        """
        return await self.restore_version(id, document, original) or await super().replace(id, document, original)

    async def get(self, req, lookup):
        """Get items based on request and lookup.

        :param req: Request object
        :param lookup: Lookup criteria
        :return: Result of super().get
        """
        req, lookup = self._get_highlight(req, lookup)
        return await super().get(req, lookup)

    async def find_one(self, req, **lookup):
        """Find a single item.

        :param req: Request object
        :param lookup: Lookup criteria
        :return: Found item
        """
        item = await super().find_one(req, **lookup)

        if item and str(item.task.stage) in get_resource_service("users").get_invisible_stages_ids(
            get_user().get("_id")
        ):
            raise SuperdeskApiError.forbiddenError(_("User does not have permissions to read the item."))

        handle_existing_data(item)
        return item

    async def restore_version(self, id, doc, original):
        """Restore an older version of an item.

        :param id: Item ID
        :param doc: Document containing version details
        :param original: Original document
        :return: Item ID if restored, None otherwise
        """
        item_id = id
        old_version = int(doc.get("old_version", 0))
        last_version = int(doc.get("last_version", 0))
        if not all([item_id, old_version, last_version]):
            return None

        old = await get_resource_service("archive_versions").find_one(
            req=None, _id_document=item_id, _current_version=old_version
        )
        if old is None:
            raise SuperdeskApiError.notFoundError(_("Invalid version {old_version}").format(old_version=old_version))

        curr = await get_resource_service(SOURCE).find_one(req=None, _id=item_id)
        if curr is None:
            raise SuperdeskApiError.notFoundError(_("Invalid item id {item_id}").format(item_id=item_id))

        if curr[VERSION] != last_version:
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

        await self.replace(id=item_id, document=old, original=curr)

        old.pop("old_version", None)
        old.pop("last_version", None)

        doc.update(old)
        return item_id

    async def duplicate_content(self, original_doc, state=None, extra_fields=None):
        """Duplicate the content including its version history.

        :param original_doc: Original document to duplicate
        :param state: State to set on the duplicated item
        :param extra_fields: Extra fields to set on the duplicated item
        :return: GUID of the duplicated article
        """
        if original_doc.get(ITEM_TYPE, "") == CONTENT_TYPE.COMPOSITE:
            for groups in original_doc.get("groups"):
                if groups.get("id") != "root":
                    associations = groups.get("refs", [])
                    for assoc in associations:
                        if assoc.get(RESIDREF):
                            item, _item_id, _endpoint = await self.packageService.get_associated_item(assoc)
                            assoc[RESIDREF] = assoc["guid"] = await self.duplicate_content(item)

        return await self.duplicate_item(original_doc, state, extra_fields)

    async def duplicate_item(self, original_doc, state=None, extra_fields=None, operation=None):
        """Duplicate an item.

        Duplicates the 'original_doc' including it's version history. If the article being duplicated is contained
        in a desk then the article state is changed to Submitted.

        :param original_doc: Original document to duplicate
        :param state: State to set on the duplicated item
        :param extra_fields: Extra fields to set on the duplicated item
        :param operation: Operation type
        :return: GUID of the duplicated article
        """
        new_doc = copy(original_doc)

        self.remove_after_copy(new_doc, extra_fields, delete_keys=["marked_for_user", "marked_for_sign_off"])
        on_duplicate_item(new_doc, original_doc, operation)
        resolve_document_version(new_doc, SOURCE, "PATCH", new_doc)

        if original_doc.get("task", {}).get("desk") is not None and new_doc.get(ITEM_STATE) != CONTENT_STATE.SUBMITTED:
            new_doc[ITEM_STATE] = CONTENT_STATE.SUBMITTED

        if state:
            new_doc[ITEM_STATE] = state

        convert_task_attributes_to_objectId(new_doc)
        transtype_metadata(new_doc)
        signals.item_duplicate.send(self, item=new_doc, original=original_doc, operation=operation)
        await get_model(ItemModel).create([new_doc])
        await self._duplicate_versions(original_doc["_id"], new_doc)
        await self._duplicate_history(original_doc["_id"], new_doc)

        app = superdesk.get_current_app().as_any()
        await app.on_archive_item_updated({"duplicate_id": new_doc["guid"]}, original_doc, operation or ITEM_DUPLICATE)

        if original_doc.get("task"):
            # Store the new task details along with this history entry
            await app.on_archive_item_updated(
                {"duplicate_id": original_doc["_id"], "task": original_doc.get("task")},
                new_doc,
                operation or ITEM_DUPLICATED_FROM,
            )
        else:
            await app.on_archive_item_updated(
                {"duplicate_id": original_doc["_id"]}, new_doc, operation or ITEM_DUPLICATED_FROM
            )

        signals.item_duplicated.send(self, item=new_doc, original=original_doc, operation=operation)

        return new_doc["guid"]

    def remove_after_copy(self, copied_item, extra_fields=None, delete_keys=None):
        """Remove properties which don't make sense to have for an item after copy.

        :param copied_item: Item to copy
        :param extra_fields: Extra fields to copy besides content fields
        :param delete_keys: Additional keys to delete
        """
        # get the archive schema keys
        archive_schema_keys = list(superdesk.get_app_config("DOMAIN")[SOURCE]["schema"].keys())
        archive_schema_keys.extend([ID_FIELD, LAST_UPDATED, DATE_CREATED, VERSION, ETAG])

        # Delete the keys that are not part of archive schema.
        keys_to_delete = [key for key in copied_item.keys() if key not in archive_schema_keys]
        keys_to_delete.extend(
            [
                ID_FIELD,
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
                "auto_publish",
            ]
        )
        if delete_keys:
            keys_to_delete.extend(delete_keys)

        if extra_fields:
            keys_to_delete = [key for key in keys_to_delete if key not in extra_fields]

        for key in keys_to_delete:
            copied_item.pop(key, None)

        # Copy should not preserve the SMS flag
        if copied_item.get("flags", {}).get("marked_for_sms", False):
            copied_item["flags"]["marked_for_sms"] = False

        task = copied_item.get("task", {})
        task.pop(LAST_PRODUCTION_DESK, None)
        task.pop(LAST_AUTHORING_DESK, None)

    async def _duplicate_versions(self, old_id, new_doc):
        """Duplicate versions for an item.

        :param old_id: ID of the original item
        :param new_doc: New document
        """
        resource_def = superdesk.get_app_config("DOMAIN")["archive"]
        version_id = versioned_id_field(resource_def)
        old_versions = await get_resource_service("archive_versions").get_from_mongo(
            req=None, lookup={version_id: old_id}
        )

        new_versions = []
        async for old_version in old_versions:
            old_version[version_id] = new_doc[ID_FIELD]
            del old_version[ID_FIELD]

            old_version["guid"] = new_doc["guid"]
            old_version["unique_name"] = new_doc["unique_name"]
            old_version["unique_id"] = new_doc["unique_id"]
            old_version["versioncreated"] = utcnow()
            if old_version[VERSION] == new_doc[VERSION]:
                old_version[ITEM_OPERATION] = new_doc[ITEM_OPERATION]
            new_versions.append(old_version)

        last_version = deepcopy(new_doc)
        last_version["_id_document"] = new_doc["_id"]
        del last_version["_id"]
        new_versions.append(last_version)
        if new_versions:
            await get_resource_service("archive_versions").post(new_versions)

    async def _duplicate_history(self, old_id, new_doc):
        """Duplicate history for an item.

        :param old_id: ID of the original item
        :param new_doc: New document
        """
        old_history_items = await get_resource_service("archive_history").get_from_mongo(
            req=None, lookup={"item_id": old_id}
        )

        new_history_items = []
        async for old_history_item in old_history_items:
            del old_history_item[ID_FIELD]
            old_history_item["item_id"] = new_doc["guid"]
            if not old_history_item.get("original_item_id"):
                old_history_item["original_item_id"] = old_id

            new_history_items.append(old_history_item)

        if new_history_items:
            await get_resource_service("archive_history").post(new_history_items)

    async def update(self, id, updates, original=None):
        """Update an item.

        :param id: Item ID
        :param updates: Updates to apply
        :param original: Original item
        """
        if updates.get(ASSOCIATIONS):
            for key, association in updates[ASSOCIATIONS].items():
                if association is None:
                    continue
                # don't set time stamp for related items
                if not is_related_content(key):
                    self._set_association_timestamps(association, updates, new=False)
                    remove_unwanted(association)

        # this needs to here as resolve_nested_documents (in eve) will add the schedule_settings
        if original and PUBLISH_SCHEDULE in updates and original[ITEM_STATE] == CONTENT_STATE.SCHEDULED:
            await self.deschedule_item(updates, original)  # this is an deschedule action

        # send signal
        signals.item_update.send(self, updates=updates, original=original)

        await super().update(id, updates, original)

        updated = copy(original)
        updated.update(updates)

        signals.item_updated.send(self, item=updated, original=original)

        if "marked_for_user" in updates:
            await self.handle_mark_user_notifications(updates, original)

    async def deschedule_item(self, updates, original):
        """Deschedule an item.

        This operation removes the item from publish queue and published collection.

        :param updates: Updates for the document
        :param original: Original document
        """
        if all(item.get("auto_publish", False) for item in (updates, original)):
            updates[PUBLISH_SCHEDULE] = None
            updates[SCHEDULE_SETTINGS] = None
        else:
            updates[PUBLISH_SCHEDULE] = original[PUBLISH_SCHEDULE]
            updates[SCHEDULE_SETTINGS] = original[SCHEDULE_SETTINGS]

        updates[ITEM_STATE] = CONTENT_STATE.PROGRESS
        updates[ITEM_OPERATION] = ITEM_DESCHEDULE
        updates["firstpublished"] = None
        # delete entry from published repo
        await get_resource_service("published").delete_by_article_id(original["_id"])

        # deschedule scheduled associations
        if superdesk.get_app_config("PUBLISH_ASSOCIATED_ITEMS"):
            associations = original.get(ASSOCIATIONS) or {}
            archive_service = get_resource_service("archive")
            for associations_key, associated_item in associations.items():
                if not associated_item:
                    continue
                orig_associated_item = await archive_service.find_one(req=None, _id=associated_item[ID_FIELD])
                if orig_associated_item and orig_associated_item.get("state") == CONTENT_STATE.SCHEDULED:
                    # deschedule associated item itself
                    await archive_service.patch(id=associated_item[ID_FIELD], updates={PUBLISH_SCHEDULE: None})
                    # update associated item info in the original
                    orig_associated_item = await archive_service.find_one(req=None, _id=associated_item[ID_FIELD])
                    orig_associated_item[PUBLISH_SCHEDULE] = None
                    orig_associated_item[SCHEDULE_SETTINGS] = {}
                    updates.setdefault(ASSOCIATIONS, {})[associations_key] = orig_associated_item

    async def can_edit(self, item, user_id):
        """Determine if the user can edit the item or not.

        :param item: Item to check
        :param user_id: User ID
        :return: Tuple of (can_edit, error_message)
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

    async def delete_by_article_ids(self, ids):
        """Remove content with specified IDs.

        :param ids: List of IDs to be removed
        """
        version_field = versioned_id_field(superdesk.get_app_config("DOMAIN")["archive_versions"])
        await get_resource_service("archive_versions").delete_action(lookup={version_field: {"$in": ids}})
        await super().delete_action({ID_FIELD: {"$in": ids}})

    def _set_association_timestamps(self, assoc_item, updates, new=True):
        """Set created/updated timestamps on an association.

        :param assoc_item: Association item
        :param updates: Updates dict
        :param new: If True, set DATE_CREATED
        """
        if isinstance(assoc_item, dict):
            assoc_item[LAST_UPDATED] = updates.get(LAST_UPDATED, datetime.datetime.now())
            if new:
                assoc_item[DATE_CREATED] = datetime.datetime.now()
            elif DATE_CREATED in assoc_item:
                del assoc_item[DATE_CREATED]

    def __is_req_for_save(self, doc):
        """Check if doc contains req_for_save key.

        :param doc: Document to check
        :return: True if request is for save
        """
        if "req_for_save" in doc:
            req_for_save = doc["req_for_save"]
            del doc["req_for_save"]

            return req_for_save == "true"

        return True

    async def validate_embargo(self, item):
        """Validate the embargo of the item.

        :param item: Item to validate
        :raises: SuperdeskApiError.badRequestError if validation fails
        """
        if item.item_type != ContentTypes.COMPOSITE:
            if item.embargo:
                embargo = item.schedule_settings.utc_embargo if item.schedule_settings else None
                if embargo:
                    if item.publish_schedule or item.state == CONTENT_STATE.SCHEDULED:
                        raise SuperdeskApiError.badRequestError(
                            _("An item can't have both Publish Schedule and Embargo")
                        )

                    if (
                        item.state not in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED, CONTENT_STATE.SCHEDULED}
                    ) and embargo <= utcnow():
                        raise SuperdeskApiError.badRequestError(_("Embargo cannot be earlier than now"))

                    if item.rewrite_of:
                        raise SuperdeskApiError.badRequestError(_("Rewrites doesn't support Embargo"))

                    if not isinstance(embargo, datetime.date) or not embargo.time():
                        raise SuperdeskApiError.badRequestError(_("Invalid Embargo"))

        elif await is_normal_package_async(item):
            if item.embargo:
                raise SuperdeskApiError.badRequestError(_("A Package doesn't support Embargo"))

            await self.packageService.check_if_any_item_in_package_has_embargo(item)

    async def _test_readonly_stage(self, item, updates=None):
        """If item is created or updated on readonly stage abort it.

        :param item: Item being edited/created
        :param updates: Item updates
        """

        def abort_if_readonly_stage(stage_id):
            stage = superdesk.get_resource_service("stages").find_one(req=None, _id=stage_id)
            if stage.get("local_readonly"):
                abort(403, response={"readonly": True})

        orig_stage_id = item.task.stage if getattr(item, "task", None) else None
        if orig_stage_id and get_user() and not item.get(INGEST_ID):
            abort_if_readonly_stage(orig_stage_id)

        if updates:
            dest_stage_id = updates.get("task", {}).get("stage")
            if dest_stage_id and get_user() and not item.get(INGEST_ID):
                abort_if_readonly_stage(dest_stage_id)

    async def _validate_updates(self, original, updates, user):
        """Validate updates to the article.

        :param original: Original item
        :param updates: Updates to apply
        :param user: User making the update
        :raises: SuperdeskApiError if validation fails
        """
        updated = deepcopy(original)
        updated.update(updates)

        await self._test_readonly_stage(original, updates)

        lock_user = original.get("lock_user", None)
        force_unlock = updates.get("force_unlock", False)
        str_user_id = str(user.get(ID_FIELD)) if user else None

        if lock_user and str(lock_user) != str_user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError(_("The item was locked by another user"))

        if original.get(ITEM_STATE) in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED}:
            raise SuperdeskApiError.forbiddenError(_("Item isn't in a valid state to be updated."))

        if updates.get("body_footer") and await is_normal_package_async(original):
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

            if updates.get(PUBLISH_SCHEDULE) and updates.get("state") != CONTENT_STATE.PUBLISHED and not force_unlock:
                validate_schedule(updated.get(SCHEDULE_SETTINGS, {}).get("utc_{}".format(PUBLISH_SCHEDULE)))

            updates[SCHEDULE_SETTINGS] = updated.get(SCHEDULE_SETTINGS, {})

        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            await self.packageService.on_update(updates, original)

        if original[ITEM_TYPE] == CONTENT_TYPE.PICTURE and not force_unlock:
            await CropService().validate_multiple_crops(updates, original)

        # update the embargo date
        update_schedule_settings(updated, EMBARGO, updated.get(EMBARGO))
        # Do the validation after Circular Reference check passes in Package Service
        if not force_unlock:
            await self.validate_embargo(updated)
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
        """Add system updates to the item.

        :param original: Original item
        :param updates: Updates to apply
        :param user: User making the update
        """
        convert_task_attributes_to_objectId(updates)
        transtype_metadata(updates, original)

        updates[ITEM_OPERATION] = ITEM_UPDATE
        updates.setdefault("original_creator", original.get("original_creator"))
        updates["versioncreated"] = utcnow()
        updates["version_creator"] = str(user.get(ID_FIELD)) if user else None

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

    async def get_expired_items(self, expiry_datetime, last_id=None, invalid_only=False):
        """Get the expired items.

        Where content state is not scheduled and the item matches given parameters

        :param expiry_datetime: Expiry datetime
        :param last_id: Last ID processed
        :param invalid_only: True to get only invalid items
        :return: Generator yielding lists of expired items
        """
        for i in range(superdesk.get_app_config("MAX_EXPIRY_LOOPS")):  # avoid blocking forever just in case
            query = {
                "bool": {
                    "must": [
                        {"range": {"expiry": {"lte": expiry_datetime}}},
                        {
                            "bool": {
                                "should": [
                                    {"exists": {"field": "task.desk"}},
                                    {"term": {ITEM_STATE: CONTENT_STATE.SPIKED}},
                                ],
                            }
                        },
                    ],
                    "must_not": [],
                }
            }

            if invalid_only:
                query["bool"]["must"].append({"term": {"expiry_status": "invalid"}})
            else:
                query["bool"]["must_not"].append({"term": {"expiry_status": "invalid"}})

            if last_id:  # elastic does not support range query on _id, so using guid
                query["bool"]["must"].append({"range": {"guid": {"gt": last_id}}})

            source = {
                "query": query,
                "sort": [{"guid": "asc"}, {"versioncreated": "asc"}],
                "size": superdesk.get_app_config("MAX_EXPIRY_QUERY_LIMIT"),
            }

            req = SearchRequest(source=source)
            cursor = await self.elastic.find(req)[0]
            items = await cursor.to_list()

            yield items  # we need to yield the empty list too to signal it's the end

            if not len(items):
                break
            else:
                try:
                    last_id = items[-1]["guid"]
                except KeyError:
                    pass

        else:
            logger.warning("get_expired_items did not finish in %d loops", superdesk.get_app_config("MAX_EXPIRY_LOOPS"))

    async def handle_mark_user_notifications(self, updates, original, add_activity=True):
        """Notify user when item is marked or unmarked.

        :param updates: Updates to apply
        :param original: Original item
        :param add_activity: Flag to add notification as activity
        """
        marked_user = marked_for_user = None
        orig_marked_user = original.get("marked_for_user", None)
        new_marked_user = updates.get("marked_for_user", None)
        by_user = get_user().get("display_name", get_user().get("username"))
        user_service = get_resource_service("users")

        if new_marked_user:
            marked_user = await user_service.find_one(req=None, _id=new_marked_user)
            marked_for_user = marked_user.get("display_name", marked_user.get("username"))

        if orig_marked_user and not new_marked_user:
            # sent when unmarking user from item
            user_list = [await user_service.find_one(req=None, _id=orig_marked_user)]
            message = 'Item "{headline}" has been unmarked by {by_user}.'.format(
                headline=original.get("headline", original.get("slugline", "item")), by_user=by_user
            )

            await self._send_mark_user_notifications(
                "item:marked",
                message,
                resource=self.resource_name,
                item=original,
                user_list=user_list,
                add_activity=add_activity,
            )
        elif marked_user and marked_for_user:
            # sent when mark item for user or mark to another user
            user_list = [marked_user]
            if new_marked_user and orig_marked_user and new_marked_user != orig_marked_user:
                user_list.append(await user_service.find_one(req=None, _id=orig_marked_user))

            message = 'Item "{headline}" has been marked for {for_user} by {by_user}.'.format(
                headline=original.get("headline", original.get("slugline", "item")),
                for_user=marked_for_user,
                by_user=by_user,
            )

            await self._send_mark_user_notifications(
                "item:marked",
                message,
                resource=self.resource_name,
                item=original,
                user_list=user_list,
                add_activity=add_activity,
                marked_for_user=marked_for_user,
            )

    async def _send_mark_user_notifications(
        self, activity_name, msg, resource=None, item=None, user_list=None, add_activity=True, **data
    ):
        """Send notifications on mark or unmark user operation.

        :param activity_name: Name of activity
        :param msg: Notification message
        :param resource: Resource name
        :param item: Item being marked/unmarked
        :param user_list: Users to notify
        :param add_activity: Flag to add notification as activity
        :param data: Additional data for notification
        """
        if item.get("type") == "text":
            link_id = item.get("guid", item.get("_id"))
        else:
            # since guid and _id do not match for the item of type picture, audio and video
            # create link using _id instead of guid for media items
            # and item_id for published media items as _id or guid does not match _id in archive for media items
            link_id = item.get("item_id") if item.get("state") in PUBLISH_STATES else item.get("_id")

        client_url = superdesk.get_app_config("CLIENT_URL", "").rstrip("/")
        link = "{}/#/workspace?item={}&action=view".format(client_url, link_id)

        if add_activity:
            await notify_and_add_activity(
                activity_name,
                msg,
                resource=resource,
                item=item,
                user_list=user_list,
                link=link,
                **data,
            )

        # send separate notification for markForUser extension
        push_notification(activity_name, item_id=item.get(ID_FIELD), user_list=user_list, extension="markForUser")

    async def get_items_chain(self, item):
        """Get the whole items chain including all previous updates, translations and original item.

        :param item: Item can be an "initial", "rewrite", or "translation"
        :return: Chain of items
        """

        async def get_item_translated_from(item):
            _item = item
            for _i in range(50):
                if item and item.get("translated_from"):
                    next_item = await self.find_one(req={}, _id=item["translated_from"])
                    if not next_item:
                        break
                    item = next_item
                else:
                    break
            else:
                logger.error(
                    "Failed to retrive an initial item from which item {} was translated from".format(_item.get("_id"))
                )
            return item

        item = await get_item_translated_from(item)
        if not item:
            return []
        # add item + translations
        items_chain = [item]
        items_chain += await self.get_item_translations(item)

        for _i in range(50):
            try:
                item = await self.find_one(req={}, _id=item["rewrite_of"])
                if not item:
                    break
                # prepend translations + update
                translations = await self.get_item_translations(item)
                items_chain = [item, *translations, *items_chain]
            except KeyError:
                # `item` is not an update, but it can be a translation
                if item and item.get("translated_from"):
                    translation_item = item
                    item = await get_item_translated_from(item)
                    # add item + translations
                    items_chain = [
                        item,
                        *[
                            i
                            for i in await self.get_item_translations(item)
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

    async def get_item_translations(self, item) -> list:
        """Get list of item's translations.

        :param item: Item to get translations for
        :return: List of translation items
        """
        translation_items = []
        if not item or not item.get("translations"):
            return translation_items

        for translation_item_id in item.get("translations", []):
            translation_item = await self.find_one(req={}, _id=translation_item_id)
            translation_items.append(translation_item)
            # get a translation of a translation and so on
            translation_items += await self.get_item_translations(translation_item)

        return translation_items

    async def _remove_from_translations(self, item):
        """Remove item from translations list of its parent.

        :param item: Item to remove from translations
        """
        if item.get("translated_from"):
            translated_from = await self.find_one(req=None, _id=item["translated_from"])
            if translated_from is None:
                return
            translations = translated_from.get("translations") or []
            updates = {"translations": [_id for _id in translations if _id != item["_id"]]}
            await self.system_update(translated_from["_id"], updates)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId

import logging
from eve.utils import config
from datetime import datetime
from dateutil.parser import parse as date_parse
from flask import current_app as app
from eve.versioning import insert_versioning_documents
from pytz import timezone
from copy import deepcopy
from dateutil.parser import parse

import superdesk
from superdesk import editor_utils
from superdesk.users.services import get_sign_off
from superdesk.utc import utcnow, get_expiry_date, local_to_utc, get_date
from superdesk import get_resource_service
from superdesk.metadata.item import (
    metadata_schema,
    ITEM_STATE,
    CONTENT_STATE,
    LINKED_IN_PACKAGES,
    BYLINE,
    SIGN_OFF,
    EMBARGO,
    ITEM_TYPE,
    CONTENT_TYPE,
    PUBLISH_SCHEDULE,
    SCHEDULE_SETTINGS,
    ASSOCIATIONS,
    LAST_AUTHORING_DESK,
    LAST_PRODUCTION_DESK,
    ITEM_EVENT_ID,
)
from superdesk.workflow import set_default_state, is_workflow_state_transition_valid
from superdesk.metadata.item import GUID_NEWSML, GUID_FIELD, GUID_TAG, not_analyzed, FAMILY_ID, INGEST_ID
from superdesk.metadata.utils import generate_guid
from superdesk.errors import SuperdeskApiError, IdentifierGenerationError
from superdesk.logging import logger
from apps.auth import get_user, get_auth  # noqa
from flask_babel import _


logger = logging.getLogger(__name__)
ARCHIVE = "archive"
CUSTOM_HATEOAS = {"self": {"title": "Archive", "href": "/archive/{_id}"}}
ITEM_OPERATION = "operation"
ITEM_CREATE = "create"
ITEM_FETCH = "fetch"
ITEM_UPDATE = "update"
ITEM_REWRITE = "rewrite"
ITEM_RESTORE = "restore"
ITEM_LINK = "link"
ITEM_UNLINK = "unlink"
ITEM_REOPEN = "reopen"
ITEM_DUPLICATE = "duplicate"
ITEM_DUPLICATED_FROM = "duplicated_from"
ITEM_DESCHEDULE = "deschedule"
ITEM_MARK = "mark"
ITEM_UNMARK = "unmark"
ITEM_RESEND = "resend"
ITEM_EXPORT_HIGHLIGHT = "export_highlight"
ITEM_CREATE_HIGHLIGHT = "create_highlight"
ITEM_CORRECTION = "correction"
ITEM_CANCEL_CORRECTION = "cancel_correction"
item_operations = [
    ITEM_CREATE,
    ITEM_FETCH,
    ITEM_UPDATE,
    ITEM_RESTORE,
    ITEM_DUPLICATE,
    ITEM_DUPLICATED_FROM,
    ITEM_DESCHEDULE,
    ITEM_REWRITE,
    ITEM_LINK,
    ITEM_UNLINK,
    ITEM_MARK,
    ITEM_UNMARK,
    ITEM_RESEND,
    ITEM_EXPORT_HIGHLIGHT,
    ITEM_CREATE_HIGHLIGHT,
]
BROADCAST_GENRE = "Broadcast Script"

# these fields are not available in ingest but available in archive, published, archived
ARCHIVE_SCHEMA_FIELDS = {
    "old_version": {
        "type": "number",
    },
    "last_version": {
        "type": "number",
    },
    "task": {"type": "dict"},
    PUBLISH_SCHEDULE: {"type": "datetime", "nullable": True},
    SCHEDULE_SETTINGS: {
        "type": "dict",
        "nullable": True,
        "schema": {
            "time_zone": {"type": "string", "nullable": True},
            "utc_publish_schedule": {"type": "datetime", "nullable": True},
            "utc_embargo": {"type": "datetime", "nullable": True},
        },
    },
    ITEM_OPERATION: {"type": "string", "allowed": item_operations, "index": "not_analyzed"},
    "event_id": {"type": "string", "mapping": not_analyzed},
    "rewritten_by": {"type": "string", "mapping": not_analyzed, "nullable": True},
    "rewrite_of": {"type": "string", "mapping": not_analyzed, "nullable": True},
    "sequence": {"type": "integer"},  # deprecated
    "associated_take_sequence": {"type": "integer"},  # deprecated
    EMBARGO: {"type": "datetime", "nullable": True},
    "broadcast": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "status": {"type": "string"},
            "master_id": {"type": "string", "mapping": not_analyzed},
            "rewrite_id": {"type": "string", "mapping": not_analyzed},
        },
    },
    "expiry_status": {"type": "string", "mapping": not_analyzed, "nullable": True},
    "original_id": {"type": "string", "mapping": not_analyzed},
}


FIELDS_TO_COPY_FOR_ASSOCIATED_ITEM = [
    "anpa_category",
    "subject",
    "slugline",
    "urgency",
    "priority",
    "footer",
    "abstract",
    "genre",
]


def get_default_source():
    return app.config.get("DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES", "")


def update_version(updates, original):
    """Increment version number if possible."""
    if config.VERSION in updates and original.get("version", 0) == 0:
        updates.setdefault("version", updates[config.VERSION])


def on_create_item(docs, repo_type=ARCHIVE):
    """Make sure item has basic fields populated."""

    for doc in docs:
        editor_utils.generate_fields(doc)
        update_dates_for(doc)
        set_original_creator(doc)

        if not doc.get(GUID_FIELD):
            doc[GUID_FIELD] = generate_guid(type=GUID_NEWSML)

        if "unique_id" not in doc:
            generate_unique_id_and_name(doc, repo_type)

        if "family_id" not in doc:
            doc["family_id"] = doc[GUID_FIELD]

        if "event_id" not in doc and repo_type != "ingest":
            doc["event_id"] = generate_guid(type=GUID_TAG)

        set_default_state(doc, CONTENT_STATE.DRAFT)
        doc.setdefault(config.ID_FIELD, doc[GUID_FIELD])

        if repo_type == ARCHIVE:
            # set the source for the article
            set_default_source(doc)

        if "profile" not in doc and app.config.get("DEFAULT_CONTENT_TYPE", None):
            doc["profile"] = app.config.get("DEFAULT_CONTENT_TYPE", None)

        copy_metadata_from_profile(doc)
        copy_metadata_from_user_preferences(doc, repo_type)

        if "language" not in doc:
            doc["language"] = app.config.get("DEFAULT_LANGUAGE", "en")

            if doc.get("task", None) and doc["task"].get("desk", None):
                desk = superdesk.get_resource_service("desks").find_one(req=None, _id=doc["task"]["desk"])
                if desk and desk.get("desk_language", None):
                    doc["language"] = desk["desk_language"]

        if not doc.get(ITEM_OPERATION):
            doc[ITEM_OPERATION] = ITEM_CREATE

        if doc.get("template"):
            from apps.templates.content_templates import render_content_template_by_id  # avoid circular import

            doc.pop("fields_meta", None)
            render_content_template_by_id(doc, doc["template"], update=True)
            editor_utils.generate_fields(doc)


def format_dateline_to_locmmmddsrc(located, current_timestamp, source=None):
    """
    Formats dateline to "Location, Month Date Source -"

    :return: formatted dateline string
    """

    if source is None:
        source = get_default_source()

    dateline_location = "{city_code}"
    dateline_location_format_fields = located.get("dateline", "city")
    dateline_location_format_fields = dateline_location_format_fields.split(",")
    if "country" in dateline_location_format_fields and "state" in dateline_location_format_fields:
        dateline_location = "{city_code}, {state_code}, {country_code}"
    elif "state" in dateline_location_format_fields:
        dateline_location = "{city_code}, {state_code}"
    elif "country" in dateline_location_format_fields:
        dateline_location = "{city_code}, {country_code}"
    dateline_location = dateline_location.format(**located)

    if located["tz"] != "UTC":
        current_timestamp = datetime.fromtimestamp(current_timestamp.timestamp(), tz=timezone(located["tz"]))
    if current_timestamp.month == 9:
        formatted_date = "Sept {}".format(current_timestamp.strftime("%-d"))
    elif 3 <= current_timestamp.month <= 7:
        formatted_date = current_timestamp.strftime("%B %-d")
    else:
        formatted_date = current_timestamp.strftime("%b %-d")

    return "{location}, {mmmdd} {source} -".format(
        location=dateline_location.upper(), mmmdd=formatted_date, source=source
    )


def set_default_source(doc):
    """Set the source for the item.

    If desk level source is specified then use that source else default from global settings.

    If the item has been ingested from another source ensure that source is preserved

    :param {dict} doc: doc where source is defined
    """

    # If the item has been ingested and the source for the provider is not the same as the system default source
    # the source must be preserved as the item has been ingested from an external agency
    if doc.get("ingest_provider"):
        provider = get_resource_service("ingest_providers").find_one(req=None, _id=doc.get("ingest_provider"))
        if not provider:
            provider = get_resource_service("search_providers").find_one(req=None, _id=doc.get("ingest_provider"))
        if provider and provider.get("source", "") != get_default_source():
            if not doc.get("source"):
                doc["source"] = provider.get("source")
            if doc.get("dateline"):
                set_dateline(doc, {})
            return

    # set the source for the article as default
    source = get_default_source()
    desk_id = doc.get("task", {}).get("desk")

    if desk_id:
        # if desk level source is specified then use that instead of the default source
        desk = get_resource_service("desks").find_one(req=None, _id=desk_id)
        source = desk.get("source") or source

    doc["source"] = source

    if not doc.get("dateline"):
        return

    set_dateline(doc, {})


def on_duplicate_item(doc, original_doc, operation=None):
    """Make sure duplicated item has basic fields populated."""

    doc[GUID_FIELD] = generate_guid(type=GUID_NEWSML)
    generate_unique_id_and_name(doc)
    doc["event_id"] = generate_guid(type=GUID_TAG)
    doc.setdefault("_id", doc[GUID_FIELD])
    set_sign_off(doc)
    doc["force_unlock"] = True
    doc[ITEM_OPERATION] = operation or ITEM_DUPLICATE
    doc["original_id"] = original_doc.get("item_id", original_doc.get("_id"))
    set_default_source(doc)


def set_dateline(updates, original):
    """Set the dateline for the item.
    :param {dict} updates: Updates related to the doc
    :param {dict} original: Original document.
    """
    if not ((updates.get("dateline") or {}).get("located") and (updates.get("dateline") or {}).get("date")):
        return

    source = updates.get("source", original.get("source")) or get_default_source()
    updates["dateline"]["source"] = source

    if isinstance(updates["dateline"].get("date"), str):
        updates["dateline"]["date"] = get_date(updates["dateline"].get("date"))

    updates["dateline"]["text"] = format_dateline_to_locmmmddsrc(
        updates["dateline"].get("located"), updates["dateline"].get("date"), source
    )


def clear_rewritten_flag(event_id, rewrite_id, rewrite_field):
    """Clears rewritten_by or rewrite_of field from the existing published and archive items.

    :param str event_id: event id of the document
    :param str rewrite_id: rewrite id of the document
    :param str rewrite_field: field name 'rewrite_of' or 'rewritten_by'
    """
    publish_service = get_resource_service("published")
    archive_service = get_resource_service(ARCHIVE)

    published_rewritten_stories = publish_service.get_rewritten_items_by_event_story(
        event_id, rewrite_id, rewrite_field
    )
    processed_items = set()
    for doc in published_rewritten_stories:
        doc_id = doc.get(config.ID_FIELD)
        publish_service.update_published_items(doc_id, rewrite_field, None)
        if doc_id not in processed_items:
            # clear the flag from the archive as well.
            archive_item = archive_service.find_one(req=None, _id=doc_id)
            archive_service.system_update(doc_id, {rewrite_field: None}, archive_item)
            processed_items.add(doc_id)
            app.on_archive_item_updated({rewrite_field: None}, archive_item, ITEM_UNLINK)


def update_dates_for(doc):
    for item in ["firstcreated", "versioncreated"]:
        doc.setdefault(item, utcnow())


def set_original_creator(doc):
    usr = get_user()
    user = str(usr.get("_id", doc.get("original_creator", "")))
    doc["original_creator"] = user


def set_sign_off(updates, original=None, repo_type=ARCHIVE, user=None):
    """Set sign_off on updates object.

    Rules:
        1. updates['sign_off'] = original['sign_off'] + sign_off of the user performing operation.
        2. If the last modified user and the user performing operation are same then sign_off shouldn't change
        3. If sign_off is received on updates, this value will be preserved
        4. If a users sign_off is already in the list then remove it an append it to the remaining
    """

    if repo_type != ARCHIVE:
        return

    user = user if user else get_user()
    if not user:
        return

    if SIGN_OFF in updates:
        return
    sign_off = get_sign_off(user)
    current_sign_off = "" if original is None else (original.get(SIGN_OFF, "") or "")

    if current_sign_off.endswith(sign_off):
        return

    # remove the sign off from the list if already there
    if not app.config.get("FULL_SIGN_OFF"):
        current_sign_off = current_sign_off.replace(sign_off + "/", "")

    updated_sign_off = "{}/{}".format(current_sign_off, sign_off)
    updates[SIGN_OFF] = updated_sign_off[1:] if updated_sign_off.startswith("/") else updated_sign_off


def generate_unique_id_and_name(item, repo_type=ARCHIVE):
    """Generates and appends unique_id and unique_name to item.

    :throws IdentifierGenerationError: if unable to generate unique_id
    """

    try:
        unique_id = get_resource_service("sequences").get_next_sequence_number(
            key_name="{}_SEQ".format(repo_type.upper())
        )
        item["unique_id"] = unique_id
        item["unique_name"] = "#" + str(unique_id)
    except Exception as e:
        raise IdentifierGenerationError() from e


def insert_into_versions(id_=None, doc=None):
    """Insert version document.

    There are some scenarios where the requests are not handled by eve. In those scenarios superdesk should be able to
    manually manage versions. Below are some scenarios:

    1.  When a user fetches content from ingest collection the request is handled by fetch API which doesn't
        extend from ArchiveResource.
    2.  When a user submits content to a desk the request is handled by /tasks API.
    3.  When a user publishes a package the items of the package also needs to be published. The publishing of items
        in the package is not handled by eve.
    """

    if id_:
        doc_in_archive_collection = get_resource_service(ARCHIVE).find_one(req=None, _id=id_)
    else:
        doc_in_archive_collection = doc

    if not doc_in_archive_collection:
        raise SuperdeskApiError.badRequestError(message=_("Document not found in archive collection"))

    remove_unwanted(doc_in_archive_collection)
    if app.config["VERSION"] in doc_in_archive_collection:
        insert_versioning_documents(ARCHIVE, doc_in_archive_collection)


def remove_unwanted(doc):
    """Remove attributes unecessary to superdesk from documents.

    As the name suggests this function removes unwanted attributes from doc to make an entry in Mongo and Elastic.
    """

    # _type attribute comes when queried against Elastic and desk comes while fetching an item from ingest
    if doc:
        for attr in ["_type", "desk", "archived"]:
            if attr in doc:
                del doc[attr]


def fetch_item(doc, desk_id, stage_id, state=None, target=None):
    dest_doc = dict(doc)

    if target:
        # set target subscriber info
        dest_doc.update(target)

    new_id = generate_guid(type=GUID_TAG)
    if doc.get("guid"):
        dest_doc.setdefault("uri", doc[GUID_FIELD])

    dest_doc[config.ID_FIELD] = new_id
    dest_doc[GUID_FIELD] = new_id
    generate_unique_id_and_name(dest_doc)

    # avoid circular import
    from apps.tasks import send_to

    dest_doc[config.VERSION] = 1
    dest_doc["versioncreated"] = utcnow()
    send_to(doc=dest_doc, desk_id=desk_id, stage_id=stage_id)
    dest_doc[ITEM_STATE] = state or CONTENT_STATE.FETCHED

    dest_doc[FAMILY_ID] = doc[config.ID_FIELD]
    dest_doc[INGEST_ID] = doc[config.ID_FIELD]
    dest_doc[ITEM_OPERATION] = ITEM_FETCH

    remove_unwanted(dest_doc)
    set_original_creator(dest_doc)
    return dest_doc


def remove_media_files(doc):
    """Removes the media files of the given doc.

    If media files are not references by any other
    story then delete the media files
    :param dict doc: document for which the media are being deleted
    :return boolean: True if files are deleted else false.
    """
    references = None

    if doc.get("renditions"):
        references = [doc.get("renditions")]

    if not references:
        references = [
            assoc.get("renditions")
            for assoc in (doc.get(ASSOCIATIONS) or {}).values()
            if assoc and assoc.get("renditions")
        ]

    if references:
        logger.info("Removing media files for %s", doc.get("guid"))

    for renditions in references:
        for rendition in renditions.values():
            media = rendition.get("media") if isinstance(rendition.get("media"), str) else str(rendition.get("media"))
            try:
                references = get_resource_service("media_references").get(
                    req=None, lookup={"media_id": media, "published": True}
                )

                if references.count() == 0:
                    logger.info("Deleting media:{}".format(rendition.get("media")))
                    app.media.delete(media)
            except Exception:
                logger.exception("Failed to remove Media Id: {} from item: {}".format(media, doc.get(config.ID_FIELD)))

    for attachment in doc.get("attachments", []):
        lookup = {"_id": attachment["attachment"]}
        get_resource_service("attachments").delete_action(lookup)


def is_assigned_to_a_desk(doc):
    """Returns True if the 'doc' is being submitted to a desk. False otherwise.

    :param doc: doc must be from archive collection
    :return: True if the 'doc' is being submitted to a desk, else False.
    """

    return doc.get("task") and doc["task"].get("desk")


def get_item_expiry(desk, stage, offset=None):
    """Calculate expiry date of the item.

    Order of precedence is:
    1. Stage Content Expiry
    2. Desk Content Expiry
    3. Default Content expiry in Settings ('CONTENT_EXPIRY_MINUTES').

    :param dict desk: desk where the item is located
    :param dict stage: stage where the item is located
    :param datetime offset: datetime passed in case of embargo.
    :return datetime: expiry datetime
    """
    expiry_minutes = app.settings["CONTENT_EXPIRY_MINUTES"]
    if stage and (stage.get("content_expiry") or 0) > 0:
        expiry_minutes = stage.get("content_expiry")
    elif desk and (desk.get("content_expiry") or 0) > 0:
        expiry_minutes = desk.get("content_expiry")

    return get_expiry_date(expiry_minutes, offset=offset)


def get_expiry(desk_id, stage_id, offset=None):
    """Calculates the expiry for an item.

    Fetches the expiry duration from one of the below
        1. desk identified by desk_id
        2. stage identified by stage_id

    :param desk_id: desk identifier
    :param stage_id: stage identifier
    :return: when the doc will expire
    """
    stage = None
    desk = None

    if desk_id:
        desk = superdesk.get_resource_service("desks").find_one(req=None, _id=desk_id)

        if not desk:
            raise SuperdeskApiError.notFoundError(_("Invalid desk identifier {desk_id}").format(desk_id=desk_id))

    if stage_id:
        stage = get_resource_service("stages").find_one(req=None, _id=stage_id)

        if not stage:
            raise SuperdeskApiError.notFoundError(_("Invalid stage identifier {stage_id}").format(stage_id=stage_id))

    return get_item_expiry(desk, stage, offset)


def set_item_expiry(update, original):
    task = update.get("task", original.get("task", {}))
    desk_id = task.get("desk", None)
    stage_id = task.get("stage", None)

    if not desk_id:
        return

    if update == {}:
        original["expiry"] = get_expiry(desk_id, stage_id)
    else:
        update["expiry"] = get_expiry(desk_id, stage_id)


def update_state(original, updates, publish_from_personal=None):
    """Updates the 'updates' with a valid state

    If the state transition valid, the content is in user's workspace and
    original['state'] is not draft then updates['state'] is set to 'draft'. If the content is in a desk then the state
    is changed to 'in-progress'.
    """

    original_state = original.get(ITEM_STATE)
    if original_state not in {
        CONTENT_STATE.INGESTED,
        CONTENT_STATE.PROGRESS,
        CONTENT_STATE.SCHEDULED,
        CONTENT_STATE.CORRECTION,
    }:
        if not is_workflow_state_transition_valid("save", original_state):
            raise superdesk.errors.InvalidStateTransitionError()
        elif is_assigned_to_a_desk(original) or (not is_assigned_to_a_desk(original) and publish_from_personal):
            updates[ITEM_STATE] = CONTENT_STATE.PROGRESS
        elif not is_assigned_to_a_desk(original):
            updates[ITEM_STATE] = CONTENT_STATE.DRAFT


def handle_existing_data(doc, pub_status_value="usable", doc_type="archive"):
    """Handles existing data.

    For now the below are handled:
        1. Sets the value of pubstatus property in metadata of doc in either ingest or archive repo
        2. Sets the value of marked_for_not_publication
    """

    if doc:
        if "pubstatus" in doc:
            doc["pubstatus"] = doc.get("pubstatus", pub_status_value).lower()

        if doc_type == "archive" and not is_flag_in_item(doc, "marked_for_not_publication"):
            set_flag(doc, "marked_for_not_publication", False)


def set_flag(doc, flag_name, flag_value):
    flags = doc.get("flags", {})
    flags[flag_name] = flag_value


def is_flag_in_item(doc, flag_name):
    return "flags" in doc and flag_name in doc.get("flags", {})


def get_flag(doc, flag_name):
    return doc.get("flags", {}).get(flag_name, False)


def validate_schedule(schedule):
    """Validates the publish schedule.

    :param datetime schedule: schedule datetime
    :raises: SuperdeskApiError.badRequestError if following cases
        - Not a valid datetime
        - Less than current utc time
    """
    if schedule:
        if not isinstance(schedule, datetime):
            raise SuperdeskApiError.badRequestError(_("Schedule date is not recognized"))
        if not schedule.date() or schedule.date().year <= 1970:
            raise SuperdeskApiError.badRequestError(_("Schedule date is not recognized"))
        if (schedule.tzinfo and schedule < utcnow()) or (
            not schedule.tzinfo and schedule < utcnow().replace(tzinfo=None)
        ):
            raise SuperdeskApiError.badRequestError(_("Schedule cannot be earlier than now"))


def update_schedule_settings(updates, field_name, value):
    """Calculates and sets the utc schedule for the given field.

    :param updates: Where the time_zone information will be read and the updated
    schedule_settings will be recorded
    :param field_name: Name of he field: either publish_schedule or embargo
    :param value: The original value
    """

    if isinstance(value, str):
        try:
            value = parse(value)
        except ValueError:
            raise SuperdeskApiError.badRequestError(_("{} date is not recognized".format(field_name)))

    schedule_settings = updates.get(SCHEDULE_SETTINGS, {}) or {}
    utc_field_name = "utc_{}".format(field_name)
    if field_name:
        tz_name = schedule_settings.get("time_zone")
        if tz_name:
            schedule_settings[utc_field_name] = local_to_utc(tz_name, value)
        else:
            schedule_settings[utc_field_name] = value
            schedule_settings["time_zone"] = None

    updates[SCHEDULE_SETTINGS] = schedule_settings


def get_utc_schedule(doc, field_name):
    """Gets the utc value of the given field.

    :param doc: Article
    :param field_name: Name of he field: either publish_schedule or embargo
    :return: the utc value of the field
    """
    utc_field_name = "utc_{}".format(field_name)
    if (
        SCHEDULE_SETTINGS not in doc
        or not doc.get(SCHEDULE_SETTINGS)
        or utc_field_name not in doc.get(SCHEDULE_SETTINGS, {})
    ):
        update_schedule_settings(doc, field_name, doc.get(field_name))

    return doc.get(SCHEDULE_SETTINGS, {}).get(utc_field_name)


def item_schema(extra=None):
    """Create schema for item.

    :param extra: extra fields to be added to schema
    """
    schema = deepcopy(ARCHIVE_SCHEMA_FIELDS)
    schema.update(metadata_schema)
    if extra:
        schema.update(extra)
    return schema


def is_item_in_package(item):
    """Checks if the passed item is a member of a package.

    :param item:
    :return: True if the item belongs to a package
    """
    return item.get(LINKED_IN_PACKAGES, None) and sum(1 for x in item.get(LINKED_IN_PACKAGES, []))


def convert_task_attributes_to_objectId(doc):
    """Set the task attributes desk, stage, user as object id

    :param doc:
    """
    task = doc.get("task", {})

    if not task:
        return

    if ObjectId.is_valid(task.get("desk")) and not isinstance(task.get("desk"), ObjectId):
        task["desk"] = ObjectId(task.get("desk"))
    if ObjectId.is_valid(task.get("stage")) and not isinstance(task.get("stage"), ObjectId):
        task["stage"] = ObjectId(task.get("stage"))
    if ObjectId.is_valid(task.get("user")) and not isinstance(task.get("user"), ObjectId):
        task["user"] = ObjectId(task.get("user"))
    if ObjectId.is_valid(task.get(LAST_PRODUCTION_DESK)) and not isinstance(task.get(LAST_PRODUCTION_DESK), ObjectId):
        task[LAST_PRODUCTION_DESK] = ObjectId(task.get(LAST_PRODUCTION_DESK))
    if ObjectId.is_valid(task.get(LAST_AUTHORING_DESK, None)) and not isinstance(
        task.get(LAST_AUTHORING_DESK), ObjectId
    ):
        task[LAST_AUTHORING_DESK] = ObjectId(task.get(LAST_AUTHORING_DESK))


def transtype_metadata(doc, original=None):
    """Change the type of metadata coming from client to match expected type in database

    Some metadata (e.g. custom fields) are sent as plain text while an other type is expected in
    database (e.g. datetime). This method check those metadata and update them.

    :param doc: document to be transtyped (will be modified in place)
    :param original: original document in case of update
    """
    # For now only fields of type "date" in the "extra" dict are handled.
    extra = doc.get("extra")
    if not extra:
        return

    if original is None:
        original = {}

    try:
        profile_id = doc.get("profile") or original["profile"]
    except KeyError:
        # profile may be missing with some items in tests
        logger.warning("`profile` is not available in doc")
        return
    ctypes_service = get_resource_service("content_types")
    profile = ctypes_service.find_one(None, _id=profile_id)
    if profile is None:
        return

    for key, value in extra.items():
        try:
            value_type = profile["schema"][key]["type"]
        except KeyError:
            continue

        if value_type == "date":
            if value and type(value) != datetime:
                try:
                    extra[key] = date_parse(value)
                except Exception as e:
                    logger.warning("Can't parse {key}: {reason}".format(key=key, reason=e))


def copy_metadata_from_profile(doc):
    """Set the default values defined on document profile.

    :param doc
    """
    defaults = {}
    profile = doc.get("profile", None)
    if profile:
        content_type = superdesk.get_resource_service("content_types").find_one(req=None, _id=profile)
        if content_type:
            defaults = {
                name: field.get("default", None)
                for (name, field) in content_type.get("schema", {}).items()
                if field and field.get("default", None)
            }

    defaults.setdefault("priority", config.DEFAULT_PRIORITY_VALUE_FOR_MANUAL_ARTICLES)
    defaults.setdefault("urgency", config.DEFAULT_URGENCY_VALUE_FOR_MANUAL_ARTICLES)
    defaults.setdefault("genre", config.DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES)
    for field in defaults:
        if field in doc and not doc[field]:
            del doc[field]
    resolve_default_values(doc, defaults)


def copy_metadata_from_user_preferences(doc, repo_type=ARCHIVE):
    """Copies following properties:

    byline, dateline.located,
    place from user preferences to doc if the repo_type is Archive and
    if the story is not fetched.

    signoff is copied for fetched and created stories

    About Dateline: Dateline has 3 parts: Located, Date (Format: Month Day) and Source. Dateline can either be simple:
    Sydney, July 30 AAP - or can be complex: Surat,Gujarat,IN, July 30 AAP -. Date in the dateline is timezone
    sensitive to the Located.  Located is set on the article based on user preferences if available. If located is not
    available in user preferences then dateline in full will not be set.
    """

    if repo_type == ARCHIVE:
        user = get_user()
        source = doc.get("source") or get_default_source()

        if doc.get("operation", "") != "fetch":
            located = user.get("user_preferences", {}).get("dateline:located", {}).get("located")
            try:
                dateline = doc["dateline"]["located"]
            except (KeyError, TypeError):
                dateline = None
            if not dateline and user and located:
                current_date_time = dateline_ts = utcnow()
                doc["dateline"] = {
                    "date": current_date_time,
                    "source": source,
                    "located": located,
                    "text": format_dateline_to_locmmmddsrc(located, dateline_ts, source),
                }

            if BYLINE not in doc and user and user.get(BYLINE):
                doc[BYLINE] = user[BYLINE]

            if "place" not in doc and user:
                place_in_preference = user.get("user_preferences", {}).get("article:default:place")

                if place_in_preference:
                    doc["place"] = place_in_preference.get("place")

        set_sign_off(doc, repo_type=repo_type, user=user)


def is_genre(item, genre_value):
    """Item to check specific genre exists or not.

    :param dict item: item on which the check is performed.
    :param str genre_value: genre_value as string
    :return: If exists then true else false
    """
    try:
        return any(genre.get("qcode", "").lower() == genre_value.lower() for genre in item.get("genre", []))
    except (AttributeError, TypeError):  # from sentry
        return False


def get_dateline_city(dateline):
    """Get the dateline city.

    :param dict dateline:
    :return str:
    """
    if not dateline:
        return ""

    if (dateline.get("located") or {}) and dateline.get("located", {}).get("city"):
        city = dateline.get("located", {}).get("city") or ""
    else:
        city = dateline.get("text") or ""
        city = city[: city.rfind(",")]

    return city


def is_media_item(doc):
    """Item is media item or not

    :param dict doc: item on which the check is performed.
    :return: If media item then true else false
    """
    return doc.get(ITEM_TYPE) in [CONTENT_TYPE.PICTURE, CONTENT_TYPE.VIDEO, CONTENT_TYPE.AUDIO]


def get_subject(doc1, doc2=None):
    """Get subject for the activity message

    :param dict doc1:
    :param dict doc2:
    """
    for key in ("headline", "slugline", "subject"):
        value = doc1.get(key)
        if not value and doc2:
            value = doc2.get(key)
        if value and key == "subject":
            value = [v.get("name") for v in value if "name" in v][0]
        if value:
            return value


# Copied from eve, as this method was removed in the following commit
# Support for Cerberus 1.1
# https://github.com/pyeve/eve/commit/2d49d2cbbed1f63e8923394c3440bb224f07c028#diff-f2ca88dfb75b2bba118053de1fc307c2
def resolve_default_values(document, defaults):
    """Add any defined default value for missing document fields.

    :param document: the document being posted or replaced
    :param defaults: tree with the default values
    :type defaults: dict

    .. versionchanged:: 0.5
       Fix #417. A default value of [] for a list causes an IndexError.

    .. versionadded:: 0.2
    """
    todo = [(defaults, document)]
    while len(todo) > 0:
        defaults, document = todo.pop()
        if isinstance(defaults, list) and len(defaults):
            todo.extend((defaults[0], item) for item in document)
            continue
        for name, value in defaults.items():
            if isinstance(value, dict):
                # default dicts overwrite simple values
                existing = document.setdefault(name, {})
                if not isinstance(existing, dict):
                    document[name] = {}
                todo.append((value, document[name]))
            if isinstance(value, list) and len(value):
                existing = document.get(name)
                if not existing:
                    document.setdefault(name, value)
                    continue
                if all(isinstance(item, (dict, list)) for item in existing):
                    todo.extend((value[0], item) for item in existing)
                else:
                    document.setdefault(name, existing)
            else:
                document.setdefault(name, value)

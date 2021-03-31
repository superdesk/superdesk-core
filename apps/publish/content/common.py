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
import superdesk
import superdesk.signals as signals

from copy import copy
from copy import deepcopy
from functools import partial
from flask import current_app as app

from superdesk import get_resource_service
from apps.content import push_content_notification
from apps.content_types.content_types import DEFAULT_SCHEMA
from superdesk.errors import InvalidStateTransitionError, SuperdeskApiError, SuperdeskValidationError
from superdesk.metadata.item import (
    CONTENT_TYPE,
    ITEM_TYPE,
    ITEM_STATE,
    CONTENT_STATE,
    PUBLISH_STATES,
    EMBARGO,
    PUB_STATUS,
    PUBLISH_SCHEDULE,
    SCHEDULE_SETTINGS,
    ASSOCIATIONS,
    MEDIA_TYPES,
)
from superdesk.metadata.packages import LINKED_IN_PACKAGES, PACKAGE, PACKAGE_TYPE
from superdesk.metadata.utils import item_url
from superdesk.notification import push_notification
from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.services import BaseService
from superdesk.utc import utcnow
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk.validation import ValidationError

from eve.utils import config
from eve.versioning import resolve_document_version

from apps.archive.archive import ArchiveResource, SOURCE as ARCHIVE
from apps.archive.common import (
    get_user,
    insert_into_versions,
    item_operations,
    FIELDS_TO_COPY_FOR_ASSOCIATED_ITEM,
    remove_unwanted,
)
from apps.archive.common import (
    validate_schedule,
    ITEM_OPERATION,
    update_schedule_settings,
    convert_task_attributes_to_objectId,
    get_expiry,
    get_utc_schedule,
    get_expiry_date,
    transtype_metadata,
)
from apps.archive.usage import track_usage, update_refs
from apps.common.components.utils import get_component
from apps.item_autosave.components.item_autosave import ItemAutosave
from apps.legal_archive.commands import import_into_legal_archive
from apps.packages.package_service import PackageService
from apps.publish.published_item import LAST_PUBLISHED_VERSION, PUBLISHED, PUBLISHED_IN_PACKAGE
from superdesk.media.crop import CropService
from superdesk.vocabularies import is_related_content
from superdesk.default_settings import strtobool
from apps.item_lock.components.item_lock import set_unlock_updates

from flask_babel import _
from flask import request, json


logger = logging.getLogger(__name__)

ITEM_PUBLISH = "publish"
ITEM_CORRECT = "correct"
ITEM_KILL = "kill"
ITEM_TAKEDOWN = "takedown"
ITEM_UNPUBLISH = "unpublish"
item_operations.extend([ITEM_PUBLISH, ITEM_CORRECT, ITEM_KILL, ITEM_TAKEDOWN, ITEM_UNPUBLISH])
publish_services = {
    ITEM_PUBLISH: "archive_publish",
    ITEM_CORRECT: "archive_correct",
    ITEM_KILL: "archive_kill",
    ITEM_TAKEDOWN: "archive_takedown",
    ITEM_UNPUBLISH: "archive_unpublish",
}

PRESERVED_FIELDS = [
    "headline",
    "byline",
    "usageterms",
    "alt_text",
    "description_text",
    "copyrightholder",
    "copyrightnotice",
]


class BasePublishResource(ArchiveResource):
    """
    Base resource class for "publish" endpoint.
    """

    def __init__(self, endpoint_name, app, service, publish_type):
        self.endpoint_name = "archive_%s" % publish_type
        self.resource_title = endpoint_name

        self.schema[PUBLISHED_IN_PACKAGE] = {"type": "string"}
        self.datasource = {"source": ARCHIVE}

        self.url = "archive/{}".format(publish_type)
        self.item_url = item_url

        self.resource_methods = []
        self.item_methods = ["PATCH"]

        self.privileges = {"PATCH": publish_type}

        super().__init__(endpoint_name, app=app, service=service)


class BasePublishService(BaseService):
    """Base service for different "publish" services."""

    publish_type = "publish"
    published_state = "published"
    item_operation = ITEM_PUBLISH

    non_digital = partial(filter, lambda s: s.get("subscriber_type", "") == SUBSCRIBER_TYPES.WIRE)
    digital = partial(
        filter, lambda s: (s.get("subscriber_type", "") in {SUBSCRIBER_TYPES.DIGITAL, SUBSCRIBER_TYPES.ALL})
    )
    package_service = PackageService()

    def on_update(self, updates, original):
        self._refresh_associated_items(original)
        self._validate(original, updates)
        self._set_updates(
            original,
            updates,
            updates.get(config.LAST_UPDATED, utcnow()),
            preserve_state=original.get("state") in (CONTENT_STATE.SCHEDULED,) and "pubstatus" not in updates,
        )
        convert_task_attributes_to_objectId(updates)  # ???
        transtype_metadata(updates, original)
        self._process_publish_updates(original, updates)
        self._mark_media_item_as_used(updates, original)
        update_refs(updates, original)

    def on_updated(self, updates, original):
        original = super().find_one(req=None, _id=original[config.ID_FIELD])
        updates.update(original)

        if updates[ITEM_OPERATION] not in {ITEM_KILL, ITEM_TAKEDOWN} and original.get(ITEM_TYPE) in [
            CONTENT_TYPE.TEXT,
            CONTENT_TYPE.PREFORMATTED,
        ]:
            get_resource_service("archive_broadcast").on_broadcast_master_updated(updates[ITEM_OPERATION], original)

        get_resource_service("archive_broadcast").reset_broadcast_status(updates, original)
        push_content_notification([updates])
        self._import_into_legal_archive(updates)
        CropService().update_media_references(updates, original, True)
        signals.item_published.send(self, item=original)
        packages = self.package_service.get_packages(original[config.ID_FIELD])
        if packages and packages.count() > 0:
            archive_correct = get_resource_service("archive_correct")
            processed_packages = []
            for package in packages:
                original_updates = {"operation": updates["operation"], ITEM_STATE: updates[ITEM_STATE]}
                if (
                    package[ITEM_STATE] in [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]
                    and package.get(PACKAGE_TYPE, "") == ""
                    and str(package[config.ID_FIELD]) not in processed_packages
                ):
                    original_updates["groups"] = package["groups"]

                    if updates.get("headline"):
                        self.package_service.update_field_in_package(
                            original_updates, original[config.ID_FIELD], "headline", updates.get("headline")
                        )

                    if updates.get("slugline"):
                        self.package_service.update_field_in_package(
                            original_updates, original[config.ID_FIELD], "slugline", updates.get("slugline")
                        )

                    archive_correct.patch(id=package[config.ID_FIELD], updates=original_updates)
                    insert_into_versions(id_=package[config.ID_FIELD])
                    processed_packages.append(package[config.ID_FIELD])

    def update(self, id, updates, original):
        """
        Handles workflow of each Publish, Corrected, Killed and TakeDown.
        """
        try:
            user = get_user()
            auto_publish = updates.get("auto_publish", False)

            # unlock the item
            set_unlock_updates(updates)

            if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                self._publish_package_items(original, updates)
                self._update_archive(original, updates, should_insert_into_versions=auto_publish)
            else:
                self._publish_associated_items(original, updates)
                updated = deepcopy(original)
                updated.update(deepcopy(updates))

                if updates.get(ASSOCIATIONS):
                    self._refresh_associated_items(updated, skip_related=True)  # updates got lost with update

                if updated.get(ASSOCIATIONS):
                    self._fix_related_references(updated, updates)

                signals.item_publish.send(self, item=updated)
                self._update_archive(original, updates, should_insert_into_versions=auto_publish)
                self.update_published_collection(published_item_id=original[config.ID_FIELD], updated=updated)

            from apps.publish.enqueue import enqueue_published

            enqueue_published.apply_async()

            push_notification(
                "item:publish",
                item=str(id),
                unique_name=original["unique_name"],
                desk=str(original.get("task", {}).get("desk", "")),
                user=str(user.get(config.ID_FIELD, "")),
            )

            if updates.get("previous_marked_user") and not updates.get("marked_for_user"):
                # send notification so that marked for me list can be updated
                get_resource_service("archive").handle_mark_user_notifications(updates, original, False)

        except SuperdeskApiError:
            raise
        except KeyError as e:
            logger.exception(e)
            raise SuperdeskApiError.badRequestError(
                message=_("Key is missing on article to be published: {exception}").format(exception=str(e))
            )
        except Exception as e:
            logger.exception(e)
            raise SuperdeskApiError.internalError(
                message=_("Failed to publish the item: {id}").format(id=str(id)), exception=e
            )

    def is_targeted(self, article, target=None):
        """Checks if article is targeted.

        Returns True if the given article has been targeted by region or
        subscriber type or specific subscribers.

        :param article: Article to check
        :param target: Optional specific target to check if exists
        :return:
        """
        if target:
            return len(article.get(target, [])) > 0
        else:
            return (
                len(
                    article.get("target_regions", [])
                    + article.get("target_types", [])
                    + article.get("target_subscribers", [])
                )
                > 0
            )

    def _validate(self, original, updates):
        self.raise_if_invalid_state_transition(original)
        self._raise_if_unpublished_related_items(original)

        updated = original.copy()
        updated.update(updates)

        self.raise_if_not_marked_for_publication(updated)

        if self.publish_type == "publish":
            # The publish schedule has not been cleared
            if (
                updates.get(PUBLISH_SCHEDULE)
                or updated.get(SCHEDULE_SETTINGS, {}).get("utc_{}".format(PUBLISH_SCHEDULE))
                or not original.get(PUBLISH_SCHEDULE)
            ):
                update_schedule_settings(updated, PUBLISH_SCHEDULE, updated.get(PUBLISH_SCHEDULE))
                validate_schedule(updated.get(SCHEDULE_SETTINGS, {}).get("utc_{}".format(PUBLISH_SCHEDULE)))

        if original[ITEM_TYPE] != CONTENT_TYPE.COMPOSITE and updates.get(EMBARGO):
            update_schedule_settings(updated, EMBARGO, updated.get(EMBARGO))
            get_resource_service(ARCHIVE).validate_embargo(updated)

        if self.publish_type in [ITEM_CORRECT, ITEM_KILL]:
            if updates.get(EMBARGO) and not original.get(EMBARGO):
                raise SuperdeskApiError.badRequestError(_("Embargo can't be set after publishing"))

        if self.publish_type == ITEM_KILL:
            if updates.get("dateline"):
                raise SuperdeskApiError.badRequestError(_("Dateline can't be modified on kill or take down"))

        if self.publish_type == ITEM_PUBLISH and updated.get("rewritten_by"):
            rewritten_by = get_resource_service(ARCHIVE).find_one(req=None, _id=updated.get("rewritten_by"))
            if rewritten_by and rewritten_by.get(ITEM_STATE) in PUBLISH_STATES:
                raise SuperdeskApiError.badRequestError(_("Cannot publish the story after Update is published."))

        if self.publish_type == ITEM_PUBLISH and updated.get("rewrite_of"):
            rewrite_of = get_resource_service(ARCHIVE).find_one(req=None, _id=updated.get("rewrite_of"))
            if rewrite_of and rewrite_of.get(ITEM_STATE) not in PUBLISH_STATES:
                raise SuperdeskApiError.badRequestError(_("Can't publish update until original story is published."))

        publish_type = "auto_publish" if updates.get("auto_publish") else self.publish_type
        validate_item = {"act": publish_type, "type": original["type"], "validate": updated}
        validation_errors = get_resource_service("validate").post([validate_item], fields=True)
        for errors, fields in validation_errors:
            if errors:
                raise SuperdeskValidationError(errors, fields)

        validation_errors = []
        self._validate_associated_items(original, updates, validation_errors)

        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            self._validate_package(original, updates, validation_errors)

        if len(validation_errors) > 0:
            raise ValidationError(validation_errors)

    def _raise_if_unpublished_related_items(self, original):
        if not request:
            return

        if (
            config.PUBLISH_ASSOCIATED_ITEMS
            or not original.get(ASSOCIATIONS)
            or self.publish_type not in [ITEM_PUBLISH, ITEM_CORRECT]
        ):
            return

        archive_service = get_resource_service("archive")
        publishing_warnings_confirmed = strtobool(request.args.get("publishing_warnings_confirmed") or "False")

        if not publishing_warnings_confirmed:
            for key, associated_item in original.get(ASSOCIATIONS).items():
                if associated_item and is_related_content(key):
                    item = archive_service.find_one(req=None, _id=associated_item.get("_id"))
                    item = item if item else associated_item

                    if item.get("state") not in PUBLISH_STATES:
                        error_msg = json.dumps(
                            {
                                "warnings": [
                                    _(
                                        "There are unpublished related "
                                        + "items that won't be sent out as "
                                        + "related items. Do you want to publish the article anyway?"
                                    )
                                ]
                            }
                        )
                        raise ValidationError(error_msg)

    def _validate_package(self, package, updates, validation_errors):
        # make sure package is not scheduled or spiked
        if package[ITEM_STATE] in (CONTENT_STATE.SPIKED, CONTENT_STATE.SCHEDULED):
            validation_errors.append(_("Package cannot be {state}").format(state=package[ITEM_STATE]))

        if package.get(EMBARGO):
            validation_errors.append(_("Package cannot have Embargo"))

        items = self.package_service.get_residrefs(package)
        if self.publish_type in [ITEM_CORRECT, ITEM_KILL]:
            removed_items, added_items = self._get_changed_items(items, updates)
            # we raise error if correction is done on a empty package. Kill is fine.
            if len(removed_items) == len(items) and len(added_items) == 0 and self.publish_type == ITEM_CORRECT:
                validation_errors.append(_("Corrected package cannot be empty!"))

    def raise_if_not_marked_for_publication(self, original):
        if original.get("flags", {}).get("marked_for_not_publication", False):
            raise SuperdeskApiError.badRequestError(_("Cannot publish an item which is marked as Not for Publication"))

    def raise_if_invalid_state_transition(self, original):
        if not is_workflow_state_transition_valid(self.publish_type, original[ITEM_STATE]):
            error_message = (
                _("Can't {operation} as item state is {state}")
                if original[ITEM_TYPE] == CONTENT_TYPE.TEXT
                else _("Can't {operation} as either package state or one of the items state is {state}")
            )
            raise InvalidStateTransitionError(
                error_message.format(operation=self.publish_type, state=original[ITEM_STATE])
            )

    def _process_publish_updates(self, original, updates):
        """Common updates for published items."""
        desk = None
        if original.get("task", {}).get("desk"):
            desk = get_resource_service("desks").find_one(req=None, _id=original["task"]["desk"])
        if not original.get("ingest_provider"):
            updates["source"] = (
                desk["source"]
                if desk and desk.get("source", "")
                else app.settings["DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES"]
            )
        updates["pubstatus"] = PUB_STATUS.CANCELED if self.publish_type == ITEM_KILL else PUB_STATUS.USABLE
        self._set_item_expiry(updates, original)

    def _set_item_expiry(self, updates, original):
        """Set the expiry for the item.

        :param dict updates: doc on which publishing action is performed
        """
        desk_id = original.get("task", {}).get("desk")
        stage_id = original.get("task", {}).get("stage")

        if EMBARGO in updates or PUBLISH_SCHEDULE in updates:
            offset = get_utc_schedule(updates, PUBLISH_SCHEDULE) or get_utc_schedule(updates, EMBARGO)
        elif EMBARGO in original or PUBLISH_SCHEDULE in original:
            offset = get_utc_schedule(original, PUBLISH_SCHEDULE) or get_utc_schedule(original, EMBARGO)

        if app.settings.get("PUBLISHED_CONTENT_EXPIRY_MINUTES"):
            updates["expiry"] = get_expiry_date(app.settings["PUBLISHED_CONTENT_EXPIRY_MINUTES"], offset=offset)
        else:
            updates["expiry"] = get_expiry(desk_id, stage_id, offset=offset)

    def _publish_package_items(self, package, updates):
        """Publishes all items of a package recursively then publishes the package itself.

        :param package: package to publish
        :param updates: payload
        """
        items = self.package_service.get_residrefs(package)

        if len(items) == 0 and self.publish_type == ITEM_PUBLISH:
            raise SuperdeskApiError.badRequestError(_("Empty package cannot be published!"))

        added_items = []
        removed_items = []
        if self.publish_type in [ITEM_CORRECT, ITEM_KILL]:
            removed_items, added_items = self._get_changed_items(items, updates)
            # we raise error if correction is done on a empty package. Kill is fine.
            if len(removed_items) == len(items) and len(added_items) == 0 and self.publish_type == ITEM_CORRECT:
                raise SuperdeskApiError.badRequestError(_("Corrected package cannot be empty!"))
            items.extend(added_items)

        if not updates.get("groups") and package.get("groups"):  # this saves some typing in tests
            updates["groups"] = package.get("groups")

        if items:
            archive_publish = get_resource_service("archive_publish")
            for guid in items:
                package_item = super().find_one(req=None, _id=guid)

                if not package_item:
                    raise SuperdeskApiError.badRequestError(
                        _("Package item with id: {guid} does not exist.").format(guid=guid)
                    )

                if package_item[ITEM_STATE] not in PUBLISH_STATES:  # if the item is not published then publish it
                    if package_item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                        # if the item is a package do recursion to publish
                        sub_updates = {i: updates[i] for i in ["state", "operation"] if i in updates}
                        sub_updates["groups"] = list(package_item["groups"])
                        self._publish_package_items(package_item, sub_updates)
                        self._update_archive(
                            original=package_item, updates=sub_updates, should_insert_into_versions=False
                        )
                    else:
                        # publish the item
                        package_item[PUBLISHED_IN_PACKAGE] = package[config.ID_FIELD]
                        archive_publish.patch(id=package_item.pop(config.ID_FIELD), updates=package_item)

                    insert_into_versions(id_=guid)

                elif guid in added_items:
                    linked_in_packages = package_item.get(LINKED_IN_PACKAGES, [])
                    if package[config.ID_FIELD] not in (lp.get(PACKAGE) for lp in linked_in_packages):
                        linked_in_packages.append({PACKAGE: package[config.ID_FIELD]})
                        super().system_update(
                            guid,
                            {LINKED_IN_PACKAGES: linked_in_packages, PUBLISHED_IN_PACKAGE: package[config.ID_FIELD]},
                            package_item,
                        )

                elif guid in removed_items:
                    # remove the package information from the package item.
                    linked_in_packages = [
                        linked
                        for linked in package_item.get(LINKED_IN_PACKAGES, [])
                        if linked.get(PACKAGE) != package.get(config.ID_FIELD)
                    ]
                    super().system_update(guid, {LINKED_IN_PACKAGES: linked_in_packages}, package_item)

                package_item = super().find_one(req=None, _id=guid)

                self.package_service.update_field_in_package(
                    updates, package_item[config.ID_FIELD], config.VERSION, package_item[config.VERSION]
                )

                if package_item.get(ASSOCIATIONS):
                    self.package_service.update_field_in_package(
                        updates, package_item[config.ID_FIELD], ASSOCIATIONS, package_item[ASSOCIATIONS]
                    )

        updated = deepcopy(package)
        updated.update(updates)
        self.update_published_collection(published_item_id=package[config.ID_FIELD], updated=updated)

    def update_published_collection(self, published_item_id, updated=None):
        """Updates the published collection with the published item.

        Set the last_published_version to false for previous versions of the published items.

        :param: str published_item_id: _id of the document.
        """
        published_item = super().find_one(req=None, _id=published_item_id)
        published_item = copy(published_item)
        if updated:
            published_item.update(updated)
        get_resource_service(PUBLISHED).update_published_items(published_item_id, LAST_PUBLISHED_VERSION, False)
        return get_resource_service(PUBLISHED).post([published_item])

    def set_state(self, original, updates):
        """Set the state of the document based on the action (publish, correction, kill, recalled)

        :param dict original: original document
        :param dict updates: updates related to document
        """
        updates[PUBLISH_SCHEDULE] = None
        updates[SCHEDULE_SETTINGS] = {}
        updates[ITEM_STATE] = self.published_state

    def _set_updates(self, original, updates, last_updated, preserve_state=False):
        """Sets config.VERSION, config.LAST_UPDATED, ITEM_STATE in updates document.

        If item is being published and embargo is available then append Editorial Note with 'Embargoed'.

        :param dict original: original document
        :param dict updates: updates related to the original document
        :param datetime last_updated: datetime of the updates.
        """
        if not preserve_state:
            self.set_state(original, updates)
        updates.setdefault(config.LAST_UPDATED, last_updated)

        if original[config.VERSION] == updates.get(config.VERSION, original[config.VERSION]):
            resolve_document_version(document=updates, resource=ARCHIVE, method="PATCH", latest_doc=original)

        user = get_user()
        if user and user.get(config.ID_FIELD):
            updates["version_creator"] = user[config.ID_FIELD]

    def _update_archive(self, original, updates, versioned_doc=None, should_insert_into_versions=True):
        """Updates the articles into archive collection and inserts the latest into archive_versions.

        Also clears autosaved versions if any.

        :param: versioned_doc: doc which can be inserted into archive_versions
        :param: should_insert_into_versions if True inserts the latest document into versions collection
        """
        self.backend.update(self.datasource, original[config.ID_FIELD], updates, original)
        app.on_archive_item_updated(updates, original, updates[ITEM_OPERATION])

        if should_insert_into_versions:
            if versioned_doc is None:
                insert_into_versions(id_=original[config.ID_FIELD])
            else:
                insert_into_versions(doc=versioned_doc)

        get_component(ItemAutosave).clear(original[config.ID_FIELD])

    def _get_changed_items(self, existing_items, updates):
        """Returns the added and removed items from existing_items.

        :param existing_items: Existing list
        :param updates: Changes
        :return: list of removed items and list of added items
        """
        if "groups" in updates:
            new_items = self.package_service.get_residrefs(updates)
            removed_items = list(set(existing_items) - set(new_items))
            added_items = list(set(new_items) - set(existing_items))
            return removed_items, added_items
        else:
            return [], []

    def _validate_associated_items(self, original_item, updates=None, validation_errors=None):
        """Validates associated items.

        This function will ensure that the unpublished content validates and none of
        the content is locked, also do not allow any killed or recalled or spiked content.

        :param package:
        :param validation_errors: validation errors are appended if there are any.
        """

        if validation_errors is None:
            validation_errors = []

        if updates is None:
            updates = {}

        # merge associations
        associations = deepcopy(original_item.get(ASSOCIATIONS, {}))
        associations.update(updates.get(ASSOCIATIONS, {}))

        items = [value for value in associations.values()]
        if original_item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and self.publish_type == ITEM_PUBLISH:
            items.extend(self.package_service.get_residrefs(original_item))

        main_publish_schedule = get_utc_schedule(updates, PUBLISH_SCHEDULE) or get_utc_schedule(
            original_item, PUBLISH_SCHEDULE
        )

        for item in items:
            orig = None
            if type(item) == dict and item.get(config.ID_FIELD):
                doc = item
                orig = super().find_one(req=None, _id=item[config.ID_FIELD])
                try:
                    doc.update({"lock_user": orig["lock_user"]})
                except (TypeError, KeyError):
                    pass
            elif item:
                doc = super().find_one(req=None, _id=item)
            else:
                continue

            if not doc:
                continue

            if not orig:
                orig = doc.copy()

            if original_item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                self._validate_associated_items(doc, validation_errors=validation_errors)

            # make sure no items are killed or recalled or spiked
            # using the latest version of the item from archive
            doc_item_state = orig.get(ITEM_STATE, CONTENT_STATE.PUBLISHED)
            if (
                doc_item_state
                in {
                    CONTENT_STATE.KILLED,
                    CONTENT_STATE.RECALLED,
                    CONTENT_STATE.SPIKED,
                }
                or (doc_item_state == CONTENT_STATE.SCHEDULED and main_publish_schedule is None)
            ):
                validation_errors.append(_("Item cannot contain associated {state} item.").format(state=doc_item_state))
            elif doc_item_state == CONTENT_STATE.SCHEDULED:
                item_schedule = get_utc_schedule(orig, PUBLISH_SCHEDULE)
                if main_publish_schedule < item_schedule:
                    validation_errors.append(_("Associated item is scheduled later than current item."))

            if doc.get(EMBARGO):
                validation_errors.append(_("Item cannot have associated items with Embargo"))

            # don't validate items that already have published
            if doc_item_state not in [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED]:
                validate_item = {"act": self.publish_type, "type": doc[ITEM_TYPE], "validate": doc}
                if type(item) == dict:
                    validate_item["embedded"] = True
                errors = get_resource_service("validate").post([validate_item], headline=True, fields=True)[0]
                if errors[0]:
                    pre_errors = [
                        _("Associated item {name} {error}").format(name=doc.get("slugline", ""), error=error)
                        for error in errors[0]
                    ]
                    validation_errors.extend(pre_errors)

            if config.PUBLISH_ASSOCIATED_ITEMS:
                # check the locks on the items
                if doc.get("lock_user"):
                    if original_item["lock_user"] != doc["lock_user"]:
                        validation_errors.extend(
                            [
                                "{}: {}".format(
                                    doc.get("headline", doc["_id"]), _("packaged item is locked by another user")
                                )
                            ]
                        )
                    elif original_item["lock_user"] == doc["lock_user"]:
                        validation_errors.extend(
                            [
                                "{}: {}".format(
                                    doc.get("headline", doc["_id"]),
                                    _("packaged item is locked by you. Unlock it and try again"),
                                )
                            ]
                        )

    def _import_into_legal_archive(self, doc):
        """Import into legal archive async

        :param {dict} doc: document to be imported
        """

        if doc.get(ITEM_STATE) != CONTENT_STATE.SCHEDULED:
            kwargs = {"item_id": doc.get(config.ID_FIELD)}
            # countdown=3 is for elasticsearch to be refreshed with archive and published changes
            import_into_legal_archive.apply_async(countdown=3, kwargs=kwargs)  # @UndefinedVariable

    def _refresh_associated_items(self, original, skip_related=False):
        """Refreshes associated items with the latest version. Any further updates made to basic metadata done after
        item was associated will be carried on and used when validating those items.
        """
        associations = original.get(ASSOCIATIONS) or {}
        for name, item in associations.items():
            if type(item) == dict and item.get(config.ID_FIELD) and (not skip_related or len(item.keys()) > 2):
                keys = [key for key in DEFAULT_SCHEMA.keys() if key not in PRESERVED_FIELDS]

                if app.settings.get("COPY_METADATA_FROM_PARENT") and item.get(ITEM_TYPE) in MEDIA_TYPES:
                    updates = original
                    keys = FIELDS_TO_COPY_FOR_ASSOCIATED_ITEM
                else:
                    updates = super().find_one(req=None, _id=item[config.ID_FIELD]) or {}

                try:
                    is_db_item_bigger_ver = updates["_current_version"] > item["_current_version"]
                except KeyError:
                    update_item_data(item, updates, keys)
                else:
                    # if copying from parent the don't keep the existing
                    # otherwise check the value is_db_item_bigger_ver
                    keep_existing = not app.settings.get("COPY_METADATA_FROM_PARENT") and not is_db_item_bigger_ver
                    update_item_data(item, updates, keys, keep_existing=keep_existing)

    def _fix_related_references(self, updated, updates):
        for key, item in updated[ASSOCIATIONS].items():
            if item and item.get("_fetchable", True) and is_related_content(key):
                updated[ASSOCIATIONS][key] = {
                    "_id": item["_id"],
                    "type": item["type"],
                    "order": item.get("order", 1),
                }
                updates.setdefault("associations", {})[key] = updated[ASSOCIATIONS][key]

    def _publish_associated_items(self, original, updates=None):
        """If there any updates to associated item and if setting:PUBLISH_ASSOCIATED_ITEMS is true
        then publish the associated item
        """

        if updates is None:
            updates = {}

        if not publish_services.get(self.publish_type):
            # publish type not supported
            return

        publish_service = get_resource_service(publish_services.get(self.publish_type))

        if not updates.get(ASSOCIATIONS) and not original.get(ASSOCIATIONS):
            # there's nothing to update
            return

        associations = original.get(ASSOCIATIONS) or {}

        if updates and updates.get(ASSOCIATIONS):
            associations.update(updates[ASSOCIATIONS])

        archive_service = get_resource_service("archive")

        for associations_key, associated_item in associations.items():
            if associated_item is None:
                continue

            if type(associated_item) == dict and associated_item.get(config.ID_FIELD):
                if not config.PUBLISH_ASSOCIATED_ITEMS or not publish_service:
                    if original.get(ASSOCIATIONS, {}).get(associations_key):
                        # Not allowed to publish
                        original[ASSOCIATIONS][associations_key]["state"] = self.published_state
                        original[ASSOCIATIONS][associations_key]["operation"] = self.publish_type
                    continue

                # if item is not fetchable, only mark it as published
                if not associated_item.get("_fetchable", True):
                    associated_item["state"] = self.published_state
                    associated_item["operation"] = self.publish_type
                    updates[ASSOCIATIONS] = updates.get(ASSOCIATIONS, {})
                    updates[ASSOCIATIONS][associations_key] = associated_item
                    continue

                if associated_item.get("state") == CONTENT_STATE.UNPUBLISHED:
                    # get the original associated item from archive
                    orig_associated_item = archive_service.find_one(req=None, _id=associated_item[config.ID_FIELD])

                    orig_associated_item["state"] = updates.get("state", self.published_state)
                    orig_associated_item["operation"] = self.publish_type

                    # if main item is scheduled we must also schedule associations
                    self._inherit_publish_schedule(original, updates, orig_associated_item)

                    get_resource_service("archive_publish").patch(
                        id=orig_associated_item.pop(config.ID_FIELD), updates=orig_associated_item
                    )
                    continue

                if associated_item.get("state") not in PUBLISH_STATES:
                    # This associated item has not been published before
                    remove_unwanted(associated_item)

                    # get the original associated item from archive
                    orig_associated_item = archive_service.find_one(req=None, _id=associated_item[config.ID_FIELD])

                    # check if the original associated item exists in archive
                    if not orig_associated_item:
                        raise SuperdeskApiError.badRequestError(
                            _('Associated item "{}" does not exist in the system'.format(associations_key))
                        )

                    if orig_associated_item.get("state") in PUBLISH_STATES:
                        # item was published already
                        original[ASSOCIATIONS][associations_key].update(
                            {
                                "state": orig_associated_item["state"],
                                "operation": orig_associated_item.get("operation", self.publish_type),
                            }
                        )
                        continue

                    # if the original associated item stage is present, it should be updated in the association item.
                    if orig_associated_item.get("task", {}).get("stage") and associated_item.get("task"):
                        associated_item["task"].update({"stage": orig_associated_item.get("task", {}).get("stage")})

                    # update _updated, otherwise it's stored as string.
                    # fixes SDESK-5043
                    associated_item["_updated"] = utcnow()

                    # if main item is scheduled we must also schedule associations
                    self._inherit_publish_schedule(original, updates, associated_item)

                    get_resource_service("archive_publish").patch(
                        id=associated_item.pop(config.ID_FIELD), updates=associated_item
                    )
                    associated_item["state"] = updates.get("state", self.published_state)
                    associated_item["operation"] = self.publish_type
                    updates[ASSOCIATIONS] = updates.get(ASSOCIATIONS, {})
                    updates[ASSOCIATIONS][associations_key] = associated_item
                elif associated_item.get("state") != self.published_state:
                    # Check if there are updates to associated item
                    association_updates = updates.get(ASSOCIATIONS, {}).get(associations_key)

                    # if main item is scheduled we must also schedule associations
                    self._inherit_publish_schedule(original, updates, associated_item)

                    if not association_updates:
                        # there is no update for this item
                        associated_item.get("task", {}).pop("stage", None)
                        remove_unwanted(associated_item)
                        publish_service.patch(id=associated_item.pop(config.ID_FIELD), updates=associated_item)
                        continue

                    if association_updates.get("state") not in PUBLISH_STATES:
                        # There's an update to the published associated item
                        remove_unwanted(association_updates)
                        publish_service.patch(id=association_updates.pop(config.ID_FIELD), updates=association_updates)

        self._refresh_associated_items(original)

    def _mark_media_item_as_used(self, updates, original):
        if ASSOCIATIONS not in updates or not updates.get(ASSOCIATIONS):
            return

        for item_name, item_obj in updates.get(ASSOCIATIONS).items():
            if not item_obj or config.ID_FIELD not in item_obj:
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

    def _inherit_publish_schedule(self, original, updates, associated_item):
        if self.publish_type == "publish" and (updates.get(PUBLISH_SCHEDULE) or original.get(PUBLISH_SCHEDULE)):
            schedule_settings = updates.get(SCHEDULE_SETTINGS, original.get(SCHEDULE_SETTINGS, {}))
            publish_schedule = updates.get(PUBLISH_SCHEDULE, original.get(PUBLISH_SCHEDULE))
            if publish_schedule and not associated_item.get(PUBLISH_SCHEDULE):
                associated_item[PUBLISH_SCHEDULE] = publish_schedule
                associated_item[SCHEDULE_SETTINGS] = schedule_settings


def get_crop(rendition):
    fields = ("CropLeft", "CropTop", "CropRight", "CropBottom")
    return {field: rendition[field] for field in fields if field in rendition}


def update_item_data(item, data, keys=None, keep_existing=False):
    """Update main item data, so only keys from default schema.

    :param dict item: item to update
    :param dict data: update date
    :param list keys: keys of item to update
    :param bool keep_existing: if True, will only set non existing values
    """
    if keys is None:
        keys = DEFAULT_SCHEMA.keys()

    for key in keys:
        if data.get(key):
            if keep_existing:
                item.setdefault(key, data[key])
            else:
                item[key] = data[key]


superdesk.workflow_state("published")
superdesk.workflow_action(
    name="publish",
    include_states=["fetched", "routed", "submitted", "in_progress", "scheduled", "unpublished", "correction"],
    privileges=["publish"],
)

superdesk.workflow_state("scheduled")
superdesk.workflow_action(
    name="schedule", include_states=["fetched", "routed", "submitted", "in_progress"], privileges=["schedule"]
)

superdesk.workflow_action(name="deschedule", include_states=["scheduled"], privileges=["deschedule"])

superdesk.workflow_state("killed")
superdesk.workflow_action(
    name="kill", include_states=["published", "scheduled", "corrected", "correction"], privileges=["kill"]
)

superdesk.workflow_state("corrected")
superdesk.workflow_action(
    name="correct", include_states=["published", "corrected", "correction"], privileges=["correct"]
)

superdesk.workflow_state("correction")
superdesk.workflow_action(
    name="correction",
    include_states=["published", "correction", "being_corrected", "corrected", "kill"],
    privileges=["correct"],
)

superdesk.workflow_action(name="rewrite", exclude_states=["killed", "spiked", "scheduled"], privileges=["rewrite"])

superdesk.workflow_state("recalled")
superdesk.workflow_action(
    name="recalled", include_states=["published", "scheduled", "corrected"], privileges=["takedown"]
)

superdesk.workflow_state("unpublished")
superdesk.workflow_action(
    name="unpublish", include_states=["published", "scheduled", "corrected"], privileges=["unpublish"]
)

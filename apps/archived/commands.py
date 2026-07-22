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
from copy import deepcopy
from datetime import timedelta

import superdesk
from eve.utils import ParsedRequest, config

from superdesk import get_resource_service
from superdesk.metadata.item import CONTENT_STATE, CONTENT_TYPE, ITEM_TYPE, PUBLISH_STATES
from superdesk.metadata.packages import LINKED_IN_PACKAGES, MAIN_GROUP, PACKAGE, PACKAGE_TYPE
from superdesk.utc import utcnow
from apps.archive.common import ARCHIVE, insert_into_versions
from apps.packages import PackageService
from apps.publish.published_item import LAST_PUBLISHED_VERSION, PUBLISH_STATE, PUBLISHED, QUEUE_STATE

logger = logging.getLogger(__name__)

ARCHIVE_SOURCE = "archive"
ARCHIVED_SOURCE = "archived"

ARCHIVED_FIELDS_TO_REMOVE = {
    "archived_id",
    "item_id",
    "queue_state",
    "publish_state",
    "error_message",
    "moved_to_legal",
    "last_queue_event",
    "publish_sequence_no",
    "is_take_item",
    "digital_item_id",
    "old_version",
    "last_version",
    "_links",
    "_type",
    config.ETAG,
}


class UnarchiveItemCommand(superdesk.Command):
    """Unarchive published articles so they can be edited/corrected.

    Example:
    ::

        $ python manage.py archived:unarchive item1 item2 --dry-run

    """

    option_list = [
        superdesk.Option("item_ids", nargs="*"),
        superdesk.Option(
            "--dry-run", "-d", dest="dry_run", action="store_true", help="Simulate without making changes"
        ),
        superdesk.Option(
            "--expiry-days",
            dest="expiry_days",
            type=int,
            default=None,
            help="Optional days until restored items expire; omit for no expiry",
        ),
    ]

    def run(self, item_ids, dry_run=False, expiry_days=None):
        """Unarchive the given item IDs.

        :param item_ids: List of item IDs (GUIDs) to unarchive.
        :param dry_run: If True, simulate without making changes.
        :param expiry_days: Optional days until restored items expire; None means no expiry.
        :return: Dict with 'success' and 'failed' lists.
        """
        item_ids = list(item_ids)

        if expiry_days is not None and expiry_days < 0:
            raise ValueError("expiry_days must be >= 0")

        if not item_ids:
            print("No item IDs provided.")
            return {"success": [], "failed": []}

        results = {"success": [], "failed": []}

        for item_id in item_ids:
            try:
                self._unarchive_item(item_id, dry_run, expiry_days)
                results["success"].append(item_id)
            except Exception as e:
                logger.error("Failed to unarchive item %s: %s", item_id, e)
                results["failed"].append({"item_id": item_id, "error": str(e)})

        print("Unarchive complete:")
        print("  Successful: {}".format(len(results["success"])))
        print("  Failed: {}".format(len(results["failed"])))

        if results["failed"]:
            print("\nFailed items:")
            for failure in results["failed"]:
                print("  - {}: {}".format(failure["item_id"], failure["error"]))

        return results

    def _unarchive_item(self, item_id, dry_run, expiry_days):
        """Unarchive a single item"""
        archived_service = get_resource_service(ARCHIVED_SOURCE)
        archive_service = get_resource_service(ARCHIVE_SOURCE)
        published_service = get_resource_service(PUBLISHED)

        latest_item = self._get_latest_archived_item(archived_service, item_id)

        # Collect items to restore (main item + direct package refs + takes package if applicable)
        items_to_restore = self._collect_items_to_restore(latest_item, archived_service)
        restore_order = (
            items_to_restore[1:] + items_to_restore[:1]
            if latest_item.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE
            else items_to_restore
        )

        # Atomic validation: check none exist in archive
        for item in items_to_restore:
            existing = archive_service.find_one(req=None, _id=item["item_id"])
            if existing:
                raise ValueError("Item already exists in archive: {}. Aborting atomic restore.".format(item["item_id"]))
            existing = published_service.find_one(req=None, item_id=item["item_id"])
            if existing:
                raise ValueError(
                    "Item already exists in published: {}. Aborting atomic restore.".format(item["item_id"])
                )

        if dry_run:
            for item in restore_order:
                logger.info("[DRY-RUN] Would unarchive item %s (version %s)", item["item_id"], item.get(config.VERSION))
            return

        # Restore all items
        restored_item_ids = []
        try:
            for item in restore_order:
                self._restore_to_archive(item, expiry_days)
                restored_item_ids.append(item["item_id"])
                self._restore_to_published(item)
        except Exception:
            self._rollback_restored_items(restored_item_ids)
            raise

        # Clean up archived
        for item in items_to_restore:
            archived_service.command_delete({"item_id": item["item_id"]})
            logger.info("Removed archived versions for item: %s", item["item_id"])

    def _get_latest_archived_item(self, archived_service, item_id):
        req = ParsedRequest()
        req.sort = '[("%s", -1)]' % config.VERSION
        req.max_results = 1
        archived_items = list(archived_service.get_from_mongo(req=req, lookup={"item_id": item_id}))

        if not archived_items:
            raise ValueError("No archived items found for item_id: {}".format(item_id))

        return archived_items[0]

    def _collect_items_to_restore(self, latest_item, archived_service):
        """Collect the main item and all takes package items for atomic restoration.

        :param latest_item: The latest archived version of the main item.
        :param archived_service: The archived service.
        :return: List of items to restore
        """
        items = [latest_item]
        seen_ids = {latest_item.get("item_id")}

        # Restore direct package members for composite packages.
        if latest_item.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE:
            for ref in PackageService().get_item_refs(latest_item):
                ref_id = ref.get("residRef")
                if not ref_id or ref_id in seen_ids:
                    continue

                try:
                    ref_item = self._get_latest_archived_item(archived_service, ref_id)
                except ValueError:
                    raise ValueError("No archived item found for package ref: {}".format(ref_id))

                items.append(ref_item)
                seen_ids.add(ref_id)

        # Check if item is part of a takes package
        takes_package_id = self._get_take_package_id(latest_item)
        if takes_package_id:
            takes_package = self._get_latest_archived_item(archived_service, takes_package_id)
            items.append(takes_package)

            # Find all takes in the package
            for ref in self._get_package_refs(takes_package):
                take_id = ref.get("residRef")
                if take_id and take_id not in seen_ids:
                    take_item = self._get_latest_archived_item(archived_service, take_id)
                    items.append(take_item)
                    seen_ids.add(take_id)

        return items

    def _get_take_package_id(self, item):
        """Get the takes package ID if the item is part of one."""
        takes_package = [
            package.get(PACKAGE) for package in item.get(LINKED_IN_PACKAGES, []) if package.get(PACKAGE_TYPE) == "takes"
        ]
        if len(takes_package) > 1:
            logger.error("Multiple takes found for item: %s", item.get(config.ID_FIELD))
        return takes_package[0] if takes_package else None

    def _get_package_refs(self, package):
        """Get refs from the takes package."""
        if not package:
            return []
        groups = package.get("groups", [])
        refs = next((group.get("refs", []) for group in groups if group.get("id") == MAIN_GROUP), [])
        return refs

    def _rollback_restored_items(self, restored_item_ids):
        if not restored_item_ids:
            return

        archive_service = get_resource_service(ARCHIVE_SOURCE)
        published_service = get_resource_service(PUBLISHED)

        for item_id in restored_item_ids:
            try:
                archive_service.delete_by_article_ids([item_id])
            except Exception:
                logger.exception("Failed to rollback archive item: %s", item_id)

            try:
                published_service.delete_by_article_id(item_id)
            except Exception:
                logger.exception("Failed to rollback published item: %s", item_id)

    def _restore_to_archive(self, item, expiry_days):
        """Restore an item to the archive collection."""
        archive_service = get_resource_service(ARCHIVE_SOURCE)
        archive_item = deepcopy(item)

        # Remove archived-only fields
        for field in ARCHIVED_FIELDS_TO_REMOVE:
            archive_item.pop(field, None)

        # Set _id to original item_id
        archive_item[config.ID_FIELD] = archive_item.pop("item_id", item["item_id"])

        # Set versioncreated and _updated
        archive_item["versioncreated"] = utcnow()
        archive_item["_updated"] = utcnow()

        # Set expiry
        self._set_expiry(archive_item, expiry_days)

        # For composites, restore ref location to archive
        if archive_item.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE:
            package_service = PackageService()
            for ref in package_service.get_item_refs(archive_item):
                ref["location"] = ARCHIVE

        # Insert into archive using create to bypass on_create hooks
        archive_service.create([archive_item])
        logger.info("Restored item to archive: %s", archive_item[config.ID_FIELD])

        # Insert into archive_versions
        insert_into_versions(doc=archive_item)
        logger.info("Inserted version for item: %s", archive_item[config.ID_FIELD])

    def _restore_to_published(self, item):
        """Restore an item to the published collection.

        Uses post so PublishedItemService.on_create runs and sets
        item_id, publish_sequence_no, and other critical defaults.
        """
        published_service = get_resource_service(PUBLISHED)
        published_doc = deepcopy(item)

        # Remove archived-only fields
        for field in ARCHIVED_FIELDS_TO_REMOVE:
            published_doc.pop(field, None)

        # Set _id to item_id so on_create maps correctly
        published_doc[config.ID_FIELD] = published_doc.pop("item_id", item["item_id"])

        # Set queue_state and last_published_version
        published_doc[QUEUE_STATE] = PUBLISH_STATE.QUEUED
        published_doc[LAST_PUBLISHED_VERSION] = True

        # Set versioncreated and _updated
        published_doc["versioncreated"] = utcnow()
        published_doc["_updated"] = utcnow()

        # Ensure state is a valid publish state
        if published_doc.get("state") not in PUBLISH_STATES:
            published_doc["state"] = CONTENT_STATE.PUBLISHED

        # Use post to trigger on_create which sets publish_sequence_no and item_id
        published_service.post([published_doc])
        logger.info("Restored item to published: %s", item["item_id"])

    def _set_expiry(self, doc, expiry_days):
        """Set expiry on the restored item.

        By default restored items do not expire.
        Use the CLI expiry-days override to opt back in.
        """
        if expiry_days is None:
            doc["expiry"] = None
            return

        doc["expiry"] = utcnow() + timedelta(days=expiry_days)


superdesk.command("archived:unarchive", UnarchiveItemCommand())

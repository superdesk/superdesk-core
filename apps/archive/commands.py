# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import functools as ft
import logging
import superdesk
import superdesk.signals as signals

from flask import current_app as app
from eve.utils import config, ParsedRequest
from copy import deepcopy
from apps.packages import PackageService
from superdesk.celery_task_utils import get_lock_id
from superdesk.utc import utcnow
from .archive import SOURCE as ARCHIVE
from superdesk.metadata.item import (
    ITEM_STATE,
    CONTENT_STATE,
    ITEM_TYPE,
    CONTENT_TYPE,
    ASSOCIATIONS,
    MEDIA_TYPES,
    PUBLISH_STATES,
)
from superdesk.lock import lock, unlock, remove_locks, touch
from superdesk.notification import push_notification
from superdesk import get_resource_service
from bson.objectid import ObjectId
from datetime import timedelta
from werkzeug.exceptions import Conflict
from .common import remove_media_files

logger = logging.getLogger(__name__)


def log_exeption(fn):
    @ft.wraps(fn)
    def inner(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            logger.exception(e)

    return inner


def _get_expired_mongo_ids_query(minutes, now):
    _datetime = now - timedelta(minutes=minutes)
    return {"_id": {"$lt": ObjectId.from_datetime(_datetime)}}


class RemoveExpiredContent(superdesk.Command):
    """Remove expired content from Superdesk.

    It removes expired items from production, published and archived colections.

    Example:
    ::

        $ python manage.py archive:remove_expired

    """

    log_msg = ""

    def run(self):
        now = utcnow()
        self.log_msg = "Expiry Time: {}.".format(now)
        logger.info("{} Starting to remove expired content at.".format(self.log_msg))
        lock_name = get_lock_id("archive", "remove_expired")

        if not lock(lock_name, expire=1800):
            logger.info("{} Remove expired content task is already running.".format(self.log_msg))
            return

        logger.info("{} Removing expired content for expiry.".format(self.log_msg))
        # all functions should be called, even the first one throw exception,
        # so they are wrapped with log_exeption
        self._remove_expired_publish_queue_items(now)
        self._remove_expired_items(now, lock_name)
        self._remove_expired_archived_items(now, lock_name)
        unlock(lock_name)

        push_notification("content:expired")
        logger.info("{} Completed remove expired content.".format(self.log_msg))

        remove_locks()

    @log_exeption
    def _remove_expired_publish_queue_items(self, now):
        expire_interval = app.config.get("PUBLISH_QUEUE_EXPIRY_MINUTES", 0)
        if expire_interval:
            expire_time = now - timedelta(minutes=expire_interval)
            logger.info("{} Removing publish queue items created before {}".format(self.log_msg, str(expire_time)))
            get_resource_service("publish_queue").delete(_get_expired_mongo_ids_query(expire_interval, now))

    @log_exeption
    def _remove_expired_items(self, expiry_datetime, lock_name):
        """Remove the expired items.

        :param datetime expiry_datetime: expiry datetime
        :param str log_msg: log message to be prefixed
        :param str lock_name: lock name to touch
        """
        logger.info("{} Starting to remove published expired items.".format(self.log_msg))
        archive_service = get_resource_service(ARCHIVE)
        published_service = get_resource_service("published")
        items_to_remove = set()
        items_to_be_archived = dict()
        items_having_issues = dict()
        preserve_published_desks = {
            desk.get(config.ID_FIELD): 1
            for desk in get_resource_service("desks").find(where={"preserve_published_content": True})
        }

        for expired_items in archive_service.get_expired_items(expiry_datetime):
            if len(expired_items) == 0:
                logger.info("{} No items found to expire.".format(self.log_msg))
                return

            if not touch(lock_name, expire=600):
                logger.warning("{} lost lock while removing expired items.".format(self.log_msg))
                return

            # delete spiked items
            self.delete_spiked_items(expired_items)

            # get killed items
            killed_items = {
                item.get(config.ID_FIELD): item
                for item in expired_items
                if item.get(ITEM_STATE) in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED}
            }

            # check if killed items imported to legal
            items_having_issues.update(self.check_if_items_imported_to_legal_archive(killed_items))

            # filter out the killed items not imported to legal.
            killed_items = {
                item_id: item for item_id, item in killed_items.items() if item_id not in items_having_issues
            }

            # Get the not killed and spiked items
            not_killed_items = {
                item.get(config.ID_FIELD): item
                for item in expired_items
                if item.get(ITEM_STATE) not in {CONTENT_STATE.KILLED, CONTENT_STATE.SPIKED, CONTENT_STATE.RECALLED}
            }

            log_msg_format = (
                "{{'_id': {_id}, 'unique_name': {unique_name}, 'version': {_current_version}, "
                "'expired_on': {expiry}}}."
            )

            # Processing items to expire
            for item_id, item in not_killed_items.items():
                item.setdefault(config.VERSION, 1)
                item.setdefault("expiry", expiry_datetime)
                item.setdefault("unique_name", "")
                expiry_msg = log_msg_format.format(**item)
                logger.info("{} Processing expired item. {}".format(self.log_msg, expiry_msg))

                processed_items = dict()
                if (
                    item_id not in items_to_be_archived
                    and item_id not in items_having_issues
                    and self._can_remove_item(item, processed_items, preserve_published_desks)
                ):
                    # item can be archived and removed from the database
                    logger.info("{} Removing item. {}".format(self.log_msg, expiry_msg))
                    logger.info("{} Items to be removed. {}".format(self.log_msg, processed_items))
                    issues = self.check_if_items_imported_to_legal_archive(processed_items)
                    if issues:
                        items_having_issues.update(processed_items)
                    else:
                        items_to_be_archived.update(processed_items)

            # all items to expire
            items_to_expire = deepcopy(items_to_be_archived)

            # check once again in items imported to legal
            items_having_issues.update(self.check_if_items_imported_to_legal_archive(items_to_expire))
            if items_having_issues:
                # remove items not imported to legal
                items_to_expire = {
                    item_id: item for item_id, item in items_to_expire.items() if item_id not in items_having_issues
                }

                # remove items not imported to legal from archived items
                items_to_be_archived = {
                    item_id: item
                    for item_id, item in items_to_be_archived.items()
                    if item_id not in items_having_issues
                }

                # items_to_be_archived might contain killed items
                for item_id, item in items_to_be_archived.items():
                    if item.get(ITEM_STATE) in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED}:
                        killed_items[item_id] = item

                # remove killed items from the items_to_be_archived
                items_to_be_archived = {
                    item_id: item
                    for item_id, item in items_to_be_archived.items()
                    if item.get(ITEM_STATE) not in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED}
                }

            # add killed items to items to expire
            items_to_expire.update(killed_items)

            # get the filter conditions
            logger.info("{} Loading filter conditions.".format(self.log_msg))
            req = ParsedRequest()
            filter_conditions = list(
                get_resource_service("content_filters").get(req=req, lookup={"is_archived_filter": True})
            )

            # move to archived collection
            logger.info("{} Archiving items.".format(self.log_msg))
            for _item_id, item in items_to_be_archived.items():
                self._move_to_archived(item, filter_conditions)

            for item_id, item in killed_items.items():
                # delete from the published collection and queue
                msg = log_msg_format.format(**item)
                try:
                    published_service.delete_by_article_id(item_id)
                    logger.info("{} Deleting killed item from published. {}".format(self.log_msg, msg))
                    items_to_remove.add(item_id)
                except Exception:
                    logger.exception("{} Failed to delete killed item from published. {}".format(self.log_msg, msg))

            if items_to_remove:
                logger.info("{} Deleting articles.: {}".format(self.log_msg, items_to_remove))
                archive_service.delete_by_article_ids(list(items_to_remove))

            for _item_id, item in items_having_issues.items():
                msg = log_msg_format.format(**item)
                try:
                    archive_service.system_update(item.get(config.ID_FIELD), {"expiry_status": "invalid"}, item)
                    logger.info("{} Setting item expiry status. {}".format(self.log_msg, msg))
                except Exception:
                    logger.exception("{} Failed to set expiry status for item. {}".format(self.log_msg, msg))

            logger.info("{} Deleting killed from archive.".format(self.log_msg))

    @log_exeption
    def _remove_expired_archived_items(self, now, lock_name):
        if not touch(lock_name, expire=600):
            logger.warning("{} Lost lock before removing expired items from archived.".format(self.log_msg))
            return
        EXPIRY_MINUTES = app.config.get("ARCHIVED_EXPIRY_MINUTES")
        EXPIRY_LIMIT = app.config.get("MAX_EXPIRY_QUERY_LIMIT", 100)
        if not EXPIRY_MINUTES:
            return
        logger.info("%s Starting to remove expired items from archived.", self.log_msg)
        archived_service = get_resource_service("archived")
        query = _get_expired_mongo_ids_query(EXPIRY_MINUTES, now)
        expired = list(archived_service.find(query, max_results=EXPIRY_LIMIT, sort="_id"))
        if not len(expired):
            logger.info("%s No items found to expire in archived.", self.log_msg)
        else:
            logger.info("%s Removing %d expired items from archived.", self.log_msg, len(expired))
        removed = archived_service.delete_docs(expired)
        for item in expired:
            if item["_id"] not in removed:
                logger.error("%s Item was not removed from archived item=%s", self.log_msg, item["item_id"])
                continue
            signals.archived_item_removed.send(archived_service, item=item)
            if not app.config.get("LEGAL_ARCHIVE") and not archived_service.find_one(req=None, item_id=item["item_id"]):
                remove_media_files(item)

    def _can_remove_item(self, item, processed_item=None, preserve_published_desks=None):
        """Recursively checks if the item can be removed.

        :param dict item: item to be remove
        :param set processed_item: processed items
        :return: True if item can be removed, False otherwise.
        """

        if processed_item is None:
            processed_item = dict()

        item_refs = []
        package_service = PackageService()
        archive_service = get_resource_service(ARCHIVE)

        if item.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE:
            # Get the item references for is package
            item_refs = package_service.get_residrefs(item)

        if item.get(ITEM_TYPE) in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            broadcast_items = get_resource_service("archive_broadcast").get_broadcast_items_from_master_story(item)
            # If master story expires then check if broadcast item is included in a package.
            # If included in a package then check the package expiry.
            item_refs.extend([broadcast_item.get(config.ID_FIELD) for broadcast_item in broadcast_items])

            if item.get("rewrite_of"):
                item_refs.append(item.get("rewrite_of"))

            if item.get("rewritten_by"):
                item_refs.append(item.get("rewritten_by"))

        # get the list of associated item ids
        if item.get(ITEM_TYPE) in MEDIA_TYPES:
            item_refs.extend(self._get_associated_items(item))

        # get item reference where this referred
        item_refs.extend(package_service.get_linked_in_package_ids(item))

        # check item refs in the ids to remove set
        is_expired = item.get("expiry") and item.get("expiry") < utcnow()

        # if the item is published or corrected and desk has preserve_published_content as true
        if (
            preserve_published_desks
            and item.get(ITEM_STATE) in {CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED}
            and item.get("task").get("desk") in preserve_published_desks
        ):
            is_expired = False

        # If the item is associated with a planning assignment and not published then preserve it
        if item.get("assignment_id") and item.get(ITEM_STATE) not in PUBLISH_STATES:
            try:
                assignment = superdesk.get_resource_service("assignments").find_one(req=None, _id=item["assignment_id"])
                if assignment is not None:
                    is_expired = False
            except KeyError:  # planning is not enabled
                pass

        if is_expired:
            # now check recursively for all references
            if item.get(config.ID_FIELD) in processed_item:
                return is_expired

            processed_item[item.get(config.ID_FIELD)] = item
            if item_refs:
                archive_items = archive_service.get_from_mongo(req=None, lookup={"_id": {"$in": item_refs}})
                for archive_item in archive_items:
                    is_expired = self._can_remove_item(archive_item, processed_item, preserve_published_desks)
                    if not is_expired:
                        break

        # If this item is not expired then it is potentially keeping it's parent alive.
        if not is_expired:
            logger.info("{} Item ID: [{}] has not expired".format(self.log_msg, item.get(config.ID_FIELD)))
        return is_expired

    def _get_associated_media_id(self, item):
        """Get the associated media id
        :param dict item:
        :return list: list of associated item ids
        """
        ids = []
        for _key, associated_item in (item.get(ASSOCIATIONS) or {}).items():
            if associated_item:
                ids.append(associated_item.get(config.ID_FIELD))
        return ids

    def _get_associated_items(self, item):
        """Get the list of item ids where the media item is associated.
        :param dict item: media item
        :return list: list of associated item ids
        """
        if item.get(ITEM_TYPE) not in MEDIA_TYPES:
            return []

        associated_items = list(
            get_resource_service("media_references").get(req=None, lookup={"associated_id": item.get(config.ID_FIELD)})
        )

        ids = set()
        for assoc in associated_items:
            ids.add(assoc["item_id"])

        # extra query just to ensure that item is not deleted
        # get the associated items from the archive collection
        archive_docs = list(get_resource_service(ARCHIVE).get_from_mongo(req=None, lookup={"_id": {"$in": list(ids)}}))
        return [doc.get(config.ID_FIELD) for doc in archive_docs]

    def _move_to_archived(self, item, filter_conditions):
        """Moves all the published version of an article to archived.

        Deletes all published version of an article in the published collection

        :param str item_id: item_id of the document
        :param list filter_conditions: list of filter conditions
        """
        published_service = get_resource_service("published")
        archived_service = get_resource_service("archived")
        archive_service = get_resource_service("archive")
        item_id = item.get(config.ID_FIELD)
        moved_to_archived = self._conforms_to_archived_filter(item, filter_conditions)
        published_items = list(published_service.get_from_mongo(req=None, lookup={"item_id": item_id}))

        try:
            if published_items:
                # moved to archive
                logger.info(
                    "{} Found {} published items for item: {}".format(self.log_msg, len(published_items), item_id)
                )
                if moved_to_archived:
                    try:
                        archived_service.post(published_items)
                        logger.info("{} Moved item to text archive for item {}.".format(self.log_msg, item_id))
                    except Conflict:
                        logger.warning("%s Item is already in text archive. item=%s", self.log_msg, item_id)
                else:
                    logger.info("{} Not Moving item to text archive for item {}.".format(self.log_msg, item_id))

                logger.info("{} Archived published item: {}".format(self.log_msg, item_id))
                published_service.delete_by_article_id(item_id)
                logger.info("{} Deleted published item. {}".format(self.log_msg, item_id))

            archive_service.delete_by_article_ids([item_id])
            logger.info("{} Deleted archive item. {}".format(self.log_msg, item_id))
        except Exception:
            failed_items = [item.get(config.ID_FIELD) for item in published_items]
            logger.exception("{} Failed to move to archived. {}".format(self.log_msg, failed_items))

    def _conforms_to_archived_filter(self, item, filter_conditions):
        """Check if the item can be moved the archived collection or not.

        :param dict item: item to be moved
        :param list filter_conditions: list of filter conditions
        :return bool: True to archive the item else False
        """
        if not filter_conditions:
            logger.info(
                "{} No filter conditions specified for Archiving item {}.".format(
                    self.log_msg, item.get(config.ID_FIELD)
                )
            )
            return True

        filter_service = get_resource_service("content_filters")
        for fc in filter_conditions:
            if filter_service.does_match(fc, item):
                logger.info(
                    "{} Filter conditions {} matched for item {}.".format(self.log_msg, fc, item.get(config.ID_FIELD))
                )
                return False

        logger.info(
            "{} No filter conditions matched Archiving item {}.".format(self.log_msg, item.get(config.ID_FIELD))
        )
        return True

    def delete_spiked_items(self, items):
        """Delete spiked items

        :param list items:
        """
        try:
            logger.info("{} deleting spiked items.".format(self.log_msg))
            spiked_ids = [
                item.get(config.ID_FIELD)
                for item in items
                if item.get(ITEM_STATE) == CONTENT_STATE.SPIKED and not self._get_associated_items(item)
            ]
            if spiked_ids:
                logger.warning("{} deleting spiked items: {}.".format(self.log_msg, spiked_ids))
                get_resource_service("archive").delete_by_article_ids(spiked_ids)
            logger.info("{} deleted spiked items. Count: {}.".format(self.log_msg, len(spiked_ids)))
        except Exception:
            logger.exception("{} Failed to delete spiked items.".format(self.log_msg))

    def check_if_items_imported_to_legal_archive(self, items_to_expire):
        """Checks if all items are moved to legal or not.

        :param dict items_to_expire:
        :return dict: dict of items having issues.
        """
        logger.info("{} checking for items in legal archive. Items: {}".format(self.log_msg, items_to_expire.keys()))

        items_not_moved_to_legal = get_resource_service("published").get_published_items_by_moved_to_legal(
            list(items_to_expire.keys()), False
        )

        items_not_moved = dict()
        if len(items_not_moved_to_legal) > 0:
            publish_items = set([item.get("item_id") for item in items_not_moved_to_legal])
            items_not_moved = {item_id: items_to_expire[item_id] for item_id in publish_items}
            logger.warning("{} Items are not moved to legal archive {}.".format(self.log_msg, publish_items))

        # get all the
        lookup = {"$and": [{"item_id": {"$in": list(items_to_expire.keys())}}, {"moved_to_legal": False}]}

        items_not_moved_to_legal = list(get_resource_service("publish_queue").get(req=None, lookup=lookup))

        if len(items_not_moved_to_legal) > 0:
            publish_queue_items = set([item.get("item_id") for item in items_not_moved_to_legal])
            items_not_moved.update({item_id: items_to_expire[item_id] for item_id in publish_queue_items})
            logger.warning(
                "{} Items are not moved to legal publish queue {}.".format(self.log_msg, publish_queue_items)
            )

        return items_not_moved


superdesk.command("archive:remove_expired", RemoveExpiredContent())

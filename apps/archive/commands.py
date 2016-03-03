# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from superdesk.notification import push_notification

import superdesk
import logging
from eve.utils import config

from apps.packages import PackageService
from superdesk.celery_task_utils import get_lock_id
from superdesk.utc import utcnow
from .archive import SOURCE as ARCHIVE
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE
from superdesk.metadata.packages import PACKAGE_TYPE, TAKES_PACKAGE
from superdesk.lock import lock, unlock
from superdesk import get_resource_service

logger = logging.getLogger(__name__)


class RemoveExpiredContent(superdesk.Command):
    log_msg = ''

    def run(self):
        now = utcnow()
        self.log_msg = 'Expiry Time: {}.'.format(now)
        logger.info('{} Starting to remove expired content at.'.format(self.log_msg))
        lock_name = get_lock_id('archive', 'remove_expired')
        if not lock(lock_name, '', expire=600):
            logger.info('{} Remove expired content task is already running.'.format(self.log_msg))
            return
        try:
            logger.info('{} Removing expired content for expiry.'.format(self.log_msg))
            self._remove_expired_items(now)
        finally:
            unlock(lock_name, '')

        push_notification('content:expired')
        logger.info('{} Completed remove expired content.'.format(self.log_msg))

    def _remove_expired_items(self, expiry_datetime):
        """
        Remove the expired items.
        :param datetime expiry_datetime: expiry datetime
        :param str log_msg: log message to be prefixed
        """
        logger.info('{} Starting to remove published expired items.'.format(self.log_msg))
        archive_service = get_resource_service(ARCHIVE)
        published_service = get_resource_service('published')

        expired_items = list(archive_service.get_expired_items(expiry_datetime))
        if len(expired_items) == 0:
            logger.info('{} No items found to expire.'.format(self.log_msg))
            return

        # delete spiked items
        self.delete_spiked_items(expired_items)

        # get killed items
        killed_items = [item for item in expired_items if item.get(ITEM_STATE) in {CONTENT_STATE.KILLED}]

        items_to_remove = set()
        items_to_be_archived = set()

        # Get the not killed and spiked items
        not_killed_items = [item for item in expired_items
                            if item.get(ITEM_STATE) not in {CONTENT_STATE.KILLED, CONTENT_STATE.SPIKED}]

        log_msg_format = "{{'_id': {_id}, 'unique_name': {unique_name}, 'version': {_current_version}, " \
                         "'expired_on': {expiry}}}."

        # Processing items to expire
        for item in not_killed_items:
            item_id = item.get(config.ID_FIELD)
            item.setdefault(config.VERSION, 1)
            item.setdefault('expiry', expiry_datetime)
            item.setdefault('unique_name', '')
            expiry_msg = log_msg_format.format(**item)
            logger.info('{} Processing expired item. {}'.format(self.log_msg, expiry_msg))

            processed_items = set()
            if item_id not in items_to_be_archived and self._can_remove_item(item, processed_items):
                # item can be archived and removed from the database
                logger.info('{} Removing item. {}'.format(self.log_msg, expiry_msg))
                logger.info('{} Items to be removed. {}'.format(self.log_msg, processed_items))
                items_to_be_archived = items_to_be_archived | processed_items

        items_to_expire = items_to_be_archived | set([item.get(config.ID_FIELD) for item in killed_items
                                                      if item.get(ITEM_STATE) == CONTENT_STATE.KILLED])

        if not self.check_if_items_imported_to_legal_archive(list(items_to_expire)):
            logger.exception('{} CANNOT EXPIRE ITEMS AS ITEMS ARE NOT MOVE TO LEGAL ARCHIVE.'.format(self.log_msg))
            return

        # move to archived collection
        logger.info('{} Archiving items.'.format(self.log_msg))
        for item in items_to_be_archived:
            self._move_to_archived(item)

        for item in killed_items:
            # delete from the published collection and queue
            msg = log_msg_format.format(**item)
            try:
                published_service.delete_by_article_id(item.get(config.ID_FIELD))
                logger.info('{} Deleting killed item from published. {}'.format(self.log_msg, msg))
                items_to_remove.add(item.get(config.ID_FIELD))
            except:
                logger.exception('{} Failed to delete killed item from published. {}'.format(self.log_msg, msg))

        if items_to_remove:
            logger.info('{} Deleting articles.: {}'.format(self.log_msg, items_to_remove))
            archive_service.delete_by_article_ids(list(items_to_remove))

        logger.info('{} Deleting killed from archive.'.format(self.log_msg))

    def _can_remove_item(self, item, processed_item=None):
        """
        Recursively checks if the item can be removed.
        :param dict item: item to be remove
        :param set processed_item: processed items
        :return: True if item can be removed, False otherwise.
        """

        if processed_item is None:
            processed_item = set()

        item_refs = []
        package_service = PackageService()
        archive_service = get_resource_service(ARCHIVE)

        if item.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE:
            # Get the item references for is package
            item_refs = package_service.get_residrefs(item)

        if item.get(PACKAGE_TYPE) == TAKES_PACKAGE or \
           item.get(ITEM_TYPE) in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            broadcast_items = get_resource_service('archive_broadcast').get_broadcast_items_from_master_story(item)
            # If master story expires then check if broadcast item is included in a package.
            # If included in a package then check the package expiry.
            item_refs.extend([broadcast_item.get(config.ID_FIELD) for broadcast_item in broadcast_items])

        # get item reference where this referred
        item_refs.extend(package_service.get_linked_in_package_ids(item))

        # check item refs in the ids to remove set
        is_expired = 'expiry' in item and item.get('expiry') < utcnow()

        if is_expired:
            # now check recursively for all references
            if item.get(config.ID_FIELD) in processed_item:
                return is_expired

            processed_item.add(item.get(config.ID_FIELD))
            if item_refs:
                archive_items = archive_service.get_from_mongo(req=None, lookup={'_id': {'$in': item_refs}})
                for archive_item in archive_items:
                    is_expired = self._can_remove_item(archive_item, processed_item)
                    if not is_expired:
                        break

        return is_expired

    def _move_to_archived(self, _id):
        """
        Moves all the published version of an article to archived.
        Deletes all published version of an article in the published collection
        :param str _id: id of the document to be moved
        """
        published_service = get_resource_service('published')
        archived_service = get_resource_service('archived')
        archive_service = get_resource_service('archive')

        published_items = list(published_service.get_from_mongo(req=None, lookup={'item_id': _id}))

        try:
            if published_items:
                archived_service.post(published_items)
                logger.info('{} Archived published item'.format(self.log_msg))
                published_service.delete_by_article_id(_id)
                logger.info('{} Deleted published item.'.format(self.log_msg))

            archive_service.delete_by_article_ids([_id])
            logger.info('{} Delete archive item.'.format(self.log_msg))
        except:
            failed_items = [item.get(config.ID_FIELD) for item in published_items]
            logger.exception('{} Failed to move to archived. {}'.format(self.log_msg, failed_items))

    def delete_spiked_items(self, items):
        """
        delete spiked items.
        :param list items:
        """
        try:
            logger.info('{} deleting spiked items.'.format(self.log_msg))
            spiked_ids = [item.get(config.ID_FIELD) for item in items
                          if item.get(ITEM_STATE) in {CONTENT_STATE.SPIKED}]
            if spiked_ids:
                logger.warning('{} deleting spiked items: {}.'.format(self.log_msg, spiked_ids))
                get_resource_service('archive').delete_by_article_ids(spiked_ids)
            logger.info('{} deleted spiked items.'.format(self.log_msg))
        except:
            logger.exception('{} Failed to delete spiked items.'.format(self.log_msg))

    def check_if_items_imported_to_legal_archive(self, item_ids):
        """
        Checks if all items are moved to legal or not
        :param list item_ids: list of item id to be verified
        :param str log_msg: log message
        :return bool: True if items in legal archive else false
        """
        logger.info('{} checking for items in legal archive. Items: {}'.format(self.log_msg, item_ids))

        items_not_moved_to_legal = get_resource_service('published').\
            get_published_items_by_moved_to_legal(item_ids, False)

        if len(items_not_moved_to_legal) > 0:
            logger.warning('{} Items are not moved to legal archive {}.'.format(self.log_msg,
                                                                                set([item.get('item_id')
                                                                                     for item in
                                                                                     items_not_moved_to_legal])))
            return False

        lookup = {
            '$and': [
                {'item_id': {'$in': item_ids}},
                {'moved_to_legal': False},
            ]
        }

        items_not_moved_to_legal = list(get_resource_service('publish_queue').get(req=None, lookup=lookup))

        if len(items_not_moved_to_legal) > 0:
            logger.warning('{} Items are not moved to legal publish queue {}.'.format(self.log_msg,
                                                                                      set([item.get('item_id')
                                                                                           for item in
                                                                                           items_not_moved_to_legal])))
            return False

        return True


superdesk.command('archive:remove_expired', RemoveExpiredContent())

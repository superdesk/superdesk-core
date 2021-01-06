# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016, 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import superdesk
from datetime import timedelta

from flask import current_app as app
from superdesk import get_resource_service
from superdesk.celery_task_utils import get_lock_id
from superdesk.lock import lock, unlock
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


class RemoveExpiredItems(superdesk.Command):
    """Remove expired items from the content_api items collection.

    By default no items expire there, you can change it using ``CONTENT_API_EXPIRY_DAYS`` config.

    Example:
    ::

        $ python manage.py content_api:remove_expired

    """

    log_msg = ""
    expiry_days = 0  # by default this should not run

    option_list = [superdesk.Option("--expiry", "-m", dest="expiry_days", required=False)]

    def run(self, expiry_days=None):
        if expiry_days:
            self.expiry_days = int(expiry_days)
        elif app.settings.get("CONTENT_API_EXPIRY_DAYS"):
            self.expiry_days = app.settings["CONTENT_API_EXPIRY_DAYS"]

        if self.expiry_days == 0:
            logger.info("Expiry days is set to 0, therefor no items will be removed.")
            return

        now = utcnow()
        self.log_msg = "Expiry Time: {}".format(now)
        logger.info("{} Starting to remove expired content_api items.".format(self.log_msg))

        lock_name = get_lock_id("content_api", "remove_expired")
        if not lock(lock_name, expire=600):
            logger.info("{} Remove expired content_api items task is already running".format(self.log_msg))
            return

        try:
            num_items_removed = self._remove_expired_items(now, self.expiry_days)
        finally:
            unlock(lock_name)

        if num_items_removed == 0:
            logger.info("{} Completed but no items were removed".format(self.log_msg))
        else:
            logger.info("{} Completed removing {} expired content_api items".format(self.log_msg, num_items_removed))

    def _remove_expired_items(self, expiry_datetime, expiry_days):
        """Remove expired items from content_api items

        :param datetime expiry_datetime: the datetime items are to expire
        :param int expiry_days: The number of days an item will be active
        """
        logger.info("{} Starting to remove expired items.".format(self.log_msg))
        items_service = get_resource_service("items")

        num_items_removed = 0
        for expired_items in items_service.get_expired_items(
            expiry_datetime=expiry_datetime, expiry_days=expiry_days, include_children=False
        ):
            items_to_remove = set()

            log_msg_format = "{{'_id': {_id}, '_updated': {_updated}, 'expired_on': {expiry}}}"
            for item in expired_items:
                item.setdefault("expiry", item["_updated"] + timedelta(days=self.expiry_days))
                expiry_msg = log_msg_format.format(**item)
                logger.info("{} Processing expired item. {}".format(self.log_msg, expiry_msg))

                for child in self._get_expired_chain(items_service, item, expiry_datetime):
                    items_to_remove.add(child["_id"])

            if items_to_remove:
                logger.info("{} Deleting items.: {}".format(self.log_msg, items_to_remove))
                num_items_removed += len(items_to_remove)
                items_service.delete_action(lookup={"_id": {"$in": list(items_to_remove)}})

        logger.info("{} Finished removing expired items from the content_api".format(self.log_msg))
        return num_items_removed

    def _get_expired_chain(self, service, parent, expiry_datetime):
        """Gets the list of expired items if they are all expired, otherwise it returns an empty list

        :param: service: The content_api items service
        :param: dict parent: The item to be removed
        :param: datetime expiry_datetime: The date and time items should be expired
        :return list: List of expired items if they're all expired, else an empty list
        """

        items = self._get_children(service, parent)
        items.append(parent)

        for item in items:
            if not self._has_expired(item, expiry_datetime):
                return []
        return items

    def _has_expired(self, item, expiry_datetime):
        """Checks if the item has expired

        :param dict item: The item to check
        :param datetime expiry_datetime: The date and time items should be expired
        :return bool: True if the item has expired, otherwise False
        """
        item.setdefault("expiry", item["_updated"] + timedelta(days=self.expiry_days))
        return item.get("expiry") <= expiry_datetime

    def _get_children(self, service, item):
        """Get the list of children to the root item using the ancestors dictionary key

        :param service: The content_api items service
        :param dict item: The root item to get the children of
        :return list: The list of children for this root item
        """
        return list(service.find({"ancestors": item["_id"]}))


superdesk.command("content_api:remove_expired", RemoveExpiredItems())

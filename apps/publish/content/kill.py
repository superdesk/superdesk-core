# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import html

from eve.versioning import resolve_document_version
from apps.templates.content_templates import render_content_template_by_name
from .common import BasePublishService, BasePublishResource, ITEM_KILL

from superdesk.types import SubscribersResource, DesksResourceModel
from superdesk.resource_fields import ID_FIELD, LAST_UPDATED
from superdesk.flask import render_template
from superdesk.metadata.item import (
    CONTENT_STATE,
    ITEM_STATE,
    PUB_STATUS,
    EMBARGO,
    SCHEDULE_SETTINGS,
    PUBLISH_SCHEDULE,
    PUBLISH_STATES,
)
from superdesk.metadata.packages import GROUPS
from superdesk import get_resource_service
from superdesk.utc import utcnow
import logging
from copy import deepcopy
from superdesk.emails import send_article_killed_email
from superdesk.errors import SuperdeskApiError
from apps.archive.common import ITEM_OPERATION, ARCHIVE, insert_into_versions_async, get_dateline_city
from apps.publish.published_item import PUBLISHED
from quart_babel import gettext as _
from enum import Enum
from bson.objectid import ObjectId
from apps.content import push_content_notification
from superdesk.publish_async.utils import get_residrefs


logger = logging.getLogger(__name__)
# what to do when the item is in a package
PACKAGE_WORKFLOW = Enum(
    "PACKAGE_WORKFLOW",
    (
        # raise an exception, the VALIDATE_ERROR_MESSAGE will be used
        "RAISE",
        # ignore, the action can be done on items in a package
        "IGNORE",
    ),
)


class KillPublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, "kill")


class KillPublishService(BasePublishService):
    """
    Handles the ``Kill`` publish action of item(s).

    Set's the ``_state`` field to ``killed``.

    :raises:
        - :class:`superdesk.errors.SuperdeskApiError.badRequestError`
            If an embargo is set
        - :class:`superdesk.errors.SuperdeskApiError.badRequestError`
            If the ``Dateline`` field was modified
        - :class:`superdesk.validation.ValidationError`
            If the item is a package and updated package has no items.
    """

    publish_type = "kill"
    published_state = "killed"
    item_operation = ITEM_KILL
    package_workflow = PACKAGE_WORKFLOW.RAISE
    VALIDATE_ERROR_MESSAGE = _("This item is in a package. It needs to be removed before the item can be killed")

    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource=datasource, backend=backend)

    async def on_update_async(self, updates, original):
        # check if we are trying to kill an item that is contained in package
        # and the package itself is not killed.

        packages = await self.package_service.get_packages_async(original[ID_FIELD])
        if self.package_workflow == PACKAGE_WORKFLOW.RAISE:
            if packages and (await packages.count()) > 0:
                async for package in packages:
                    if package[ITEM_STATE] not in {
                        CONTENT_STATE.KILLED,
                        CONTENT_STATE.RECALLED,
                        CONTENT_STATE.UNPUBLISHED,
                    }:
                        raise SuperdeskApiError.badRequestError(message=self.VALIDATE_ERROR_MESSAGE)
        elif self.package_workflow not in PACKAGE_WORKFLOW:
            raise ValueError("Invalid package workflow")

        updates["pubstatus"] = PUB_STATUS.CANCELED
        updates["versioncreated"] = utcnow()

        await super().on_update_async(updates, original)
        updates[ITEM_OPERATION] = self.item_operation
        await self._remove_marked_user(original)
        await get_resource_service("archive_broadcast").spike_item(original)

    async def update_async(self, id, updates, original, raise_errors: bool = False):
        """Kill will broadcast kill email notice to all subscriber in the system and then kill the item.

        Kill for multiple items is triggered
        - for broadcast items if master item is killed.
        In case of the multiple items the kill header text will be different but rest
        of the body_html will be same.

        If any other fields needs in the kill template that needs to be based on the item that is being
        killed (not the item that is being actioned on) then modify the article_killed_override.json file'
        """
        # kill cannot be scheduled and embargoed.
        updates[EMBARGO] = None
        updates[PUBLISH_SCHEDULE] = None
        updates[SCHEDULE_SETTINGS] = {}
        updates_copy = deepcopy(updates)
        original_copy = deepcopy(original)
        await self.apply_kill_override(original_copy, updates)
        await self.broadcast_kill_email(original, updates)
        await super().update_async(id, updates, original, raise_errors)
        updated = deepcopy(original)
        updated.update(updates)
        await self.kill_broadcast(updates_copy, original_copy, self.item_operation)

    async def broadcast_kill_email(self, original, updates):
        """Sends the broadcast email to all subscribers (including in-active subscribers)

        :param dict original: Document to kill
        :param dict updates: kill updates
        """
        # Get all subscribers

        recipients = await SubscribersResource.get_emails()
        # send kill email.
        kill_article = deepcopy(original)
        kill_article["body_html"] = updates.get("body_html")
        kill_article["headline"] = updates.get("headline")
        kill_article["desk_name"] = await DesksResourceModel.get_desk_name(kill_article.get("task", {}).get("desk"))
        kill_article["city"] = get_dateline_city(kill_article.get("dateline"))
        kill_article["action"] = self.item_operation
        await send_article_killed_email(kill_article, recipients, utcnow())

    async def kill_item(self, updates, original):
        """Kill the item after applying the template.

        :param dict updates:
        :param dict original:
        """
        # apply the kill template
        original_copy = deepcopy(original)

        updates_data = await self.apply_kill_template(original_copy)
        updates_data["body_html"] = updates.get("body_html", "")

        # resolve the document version
        resolve_document_version(document=updates_data, resource=ARCHIVE, method="PATCH", latest_doc=original)
        # kill the item
        await self.patch_async(original.get(ID_FIELD), updates_data)
        # insert into versions
        await insert_into_versions_async(id_=original[ID_FIELD])

    async def apply_kill_template(self, item):
        # apply the kill template
        updates = await render_content_template_by_name(item, self.item_operation)
        return updates

    async def apply_kill_override(self, item, updates):
        """Applies kill override.

        Kill requires content to be generate based on the item getting killed (and not the
        item that is being actioned on).

        :param dict item: item to kill
        :param dict updates: updates that needs to be modified based on the template
        :return:
        """
        try:
            if item.get("_type") == "archive":
                # attempt to find the published item as this will have an accurate time of publication
                published_item = await get_resource_service(PUBLISHED).get_last_published_version(item.get(ID_FIELD))
                versioncreated = (
                    published_item.get("versioncreated")
                    if published_item
                    else item.get("versioncreated", item.get(LAST_UPDATED))
                )
            else:
                versioncreated = item.get("versioncreated", item.get(LAST_UPDATED))
            desk_name = await DesksResourceModel.get_desk_name(item.get("task", {}).get("desk"))
            city = get_dateline_city(item.get("dateline"))
            kill_header = json.loads(
                await render_template(
                    "article_killed_override.json",
                    slugline=item.get("slugline", ""),
                    headline=item.get("headline", ""),
                    desk_name=desk_name,
                    city=city,
                    versioncreated=versioncreated,
                    body_html=updates.get("body_html", ""),
                    update_headline=updates.get("headline", ""),
                    item_operation=self.item_operation.lower(),
                ),
                strict=False,
            )

            for key, value in kill_header.items():
                kill_header[key] = html.unescape(value)

            updates.update(kill_header)
        except Exception:
            logger.exception("Failed to apply kill header template to item {}.".format(item))

    async def _remove_marked_user(self, item):
        """Remove the marked_for_user from all the published items having same 'item_id' as item being killed."""
        item_id = item.get("_id")
        if not item_id:
            return

        updates = {"marked_for_user": None, "marked_for_sign_off": None}
        published_service = get_resource_service(PUBLISHED)

        published_items = await (
            await published_service.get_from_mongo_async(req=None, lookup={"item_id": item_id})
        ).to_list()
        if not published_items:
            return

        for item in published_items:
            if item and item.get("marked_for_user"):
                updated = item.copy()
                updated.update(updates)

                await published_service.system_update_async(ObjectId(item.get("_id")), updates, item)
                # send notifications so that list can be updated in the client
                await get_resource_service("archive").handle_mark_user_notifications(updates, item, False)
                push_content_notification([updated, item])

    async def kill_broadcast(self, updates: dict, original: dict, operation: str) -> None:
        """Kill the broadcast items

        :param dict updates: Updates to the item
        :param dict original: original item
        :param str operation: Kill or Takedown operation
        :return:
        """
        broadcast_items = [
            item
            for item in await get_resource_service("archive_broadcast").get_broadcast_items_from_master_story(original)
            if item.get(ITEM_STATE) in PUBLISH_STATES
        ]
        correct_service = get_resource_service("archive_correct")

        for item in broadcast_items:
            item_id = item.get(ID_FIELD)
            packages = await self.package_service.get_packages_async(item_id)

            processed_packages = set()
            async for package in packages:
                if str(package[ID_FIELD]) in processed_packages or package.get(ITEM_STATE) == CONTENT_STATE.RECALLED:
                    continue
                try:
                    if package.get(ITEM_STATE) in {CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED}:
                        package_updates = {
                            LAST_UPDATED: utcnow(),
                            GROUPS: self.package_service.remove_group_ref(package, item_id),
                        }

                        refs = get_residrefs(package_updates)
                        if refs:
                            await correct_service.patch_async(package[ID_FIELD], package_updates)
                        else:
                            package_updates["body_html"] = updates.get("body_html", "")
                            await self.patch_async(package[ID_FIELD], package_updates)

                        processed_packages.add(package.get(ID_FIELD))
                    else:
                        package_list = await self.package_service.remove_refs_in_package_async(
                            package, item_id, processed_packages
                        )
                        processed_packages = processed_packages.union(set(package_list))
                except Exception:
                    package_id = package.get(ID_FIELD)
                    logger.exception(f"Failed to remove the broadcast item {item_id} from package {package_id}")

            await self.kill_item(updates, item)

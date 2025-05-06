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
from eve.utils import ParsedRequest

from superdesk.core import get_current_app
from superdesk.resource_fields import ID_FIELD
from superdesk import get_resource_service
from superdesk.eve_async import AsyncBaseService
from superdesk.notification import push_notification
from apps.archive.common import get_user
from superdesk.utc import utcnow
from apps.archive.common import ITEM_MARK, ITEM_UNMARK


async def get_marked_items(desk_id):
    """Get items marked for given desk"""
    query = {
        "query": {"filtered": {"filter": {"term": {"marked_desks.desk_id": str(desk_id)}}}},
        "sort": [{"versioncreated": "desc"}],
        "size": 200,
    }
    request = ParsedRequest()
    request.args = {"source": json.dumps(query), "repo": "archive,published"}
    return await (await get_resource_service("search").get_async(req=request, lookup=None)).to_list()


class MarkedForDesksService(AsyncBaseService):
    async def create_async(self, docs, **kwargs):
        """Toggle marked desk status for given desk and item."""

        service = get_resource_service("archive")
        published_service = get_resource_service("published")
        ids = []
        for doc in docs:
            item = await service.find_one_async(req=None, _id=doc["marked_item"])
            if not item:
                ids.append(None)
                continue
            ids.append(item["_id"])
            marked_desks = item.get("marked_desks", [])
            if not marked_desks:
                marked_desks = []

            existing_mark = next((m for m in marked_desks if m["desk_id"] == doc["marked_desk"]), None)

            if existing_mark:
                # there is an existing mark so this is un-mark action
                marked_desks = [m for m in marked_desks if m["desk_id"] != doc["marked_desk"]]
                marked_desks_on = False  # highlight toggled off
            else:
                # there is no existing mark so this is mark action
                user = get_user() or {}
                new_mark = {}
                new_mark["desk_id"] = doc["marked_desk"]
                new_mark["user_marked"] = str(user.get(ID_FIELD, ""))
                new_mark["date_marked"] = utcnow()
                marked_desks.append(new_mark)
                marked_desks_on = True

            updates = {"marked_desks": marked_desks}
            await service.system_update_async(item["_id"], updates, item)

            published_items = await published_service.find_async({"item_id": item["_id"]})
            async for published_item in published_items:
                if published_item["_current_version"] == item["_current_version"] or not marked_desks_on:
                    updates = {"marked_desks": marked_desks}
                    await published_service.system_update_async(published_item["_id"], updates, published_item)

            push_notification(
                "item:marked_desks", marked=int(marked_desks_on), item_id=item["_id"], mark_id=str(doc["marked_desk"])
            )

            app = get_current_app().as_any()
            if marked_desks_on:
                await app.on_archive_item_updated.call_async({"desk_id": doc["marked_desk"]}, item, ITEM_MARK)
            else:
                await app.on_archive_item_updated.call_async({"desk_id": doc["marked_desk"]}, item, ITEM_UNMARK)

        return ids

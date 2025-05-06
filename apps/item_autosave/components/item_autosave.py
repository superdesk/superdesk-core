# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from ..models.item_autosave import ItemAutosaveModel
from apps.common.components.base_component import BaseComponent
from apps.common.models.utils import get_model
from apps.item_lock.models.item import ItemModel
from superdesk.errors import SuperdeskApiError
from quart_babel import gettext as _


class ItemAutosave(BaseComponent):
    def __init__(self, app):
        self.app = app

    @classmethod
    def name(cls):
        return "archive_autosave"

    async def autosave(self, item_id, updates, user, etag):
        updates.setdefault("_type", "archive")
        item_model = get_model(ItemModel)
        item = await item_model.find_one_async({"_id": item_id})
        if item is None:
            raise SuperdeskApiError.notFoundError(_("Invalid item identifier"))

        lock_user = item.get("lock_user", None)
        if lock_user and str(lock_user) != str(user["_id"]):
            raise SuperdeskApiError.forbiddenError(_("The item was locked by another user"))

        autosave_model = get_model(ItemAutosaveModel)
        item.update(updates)
        self.app.on_item_autosave(item)
        autosave_item = await autosave_model.find_one_async({"_id": item_id})
        if not autosave_item:
            await autosave_model.create_async([item])
        else:
            await autosave_model.update_async({"_id": item_id}, item, etag)
        await self.app.on_item_autosaved.call_async(item)
        updates.update(item)
        return updates

    async def clear(self, item_id):
        autosave_model = get_model(ItemAutosaveModel)
        return await autosave_model.delete_async({"_id": item_id})

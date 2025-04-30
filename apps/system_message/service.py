# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.resource_fields import ID_FIELD
from superdesk.eve_async import AsyncBaseService
from superdesk.notification import push_notification
from apps.auth import get_user_id


class SystemMessagesService(AsyncBaseService):
    async def on_create_async(self, docs):
        for doc in docs:
            doc["user_id"] = get_user_id()

    async def on_created_async(self, docs):
        """
        Send notification
        :param docs:
        :return:
        """
        push_notification("system_message:created", _id=[doc.get(ID_FIELD) for doc in docs])

    async def on_update_async(self, updates, original):
        updates["user_id"] = get_user_id()

    async def on_updated_async(self, updates, original):
        """
        Send notifification
        :param updates:
        :param original:
        :return:
        """
        push_notification("system_message:updated", _id=[original.get(ID_FIELD)])

    async def on_deleted_async(self, doc):
        """
        Send a notification
        :param doc:
        :return:
        """
        push_notification("system_message:deleted", _id=[doc.get(ID_FIELD)])

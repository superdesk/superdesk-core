# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.services import Service
from superdesk.notification import push_notification

from eve.utils import config
from apps.auth import get_user_id


class SystemMessagesService(Service):
    def on_create(self, docs):
        for doc in docs:
            doc["user_id"] = get_user_id()

    def on_created(self, docs):
        """
        Send notification
        :param docs:
        :return:
        """
        push_notification("system_message:created", _id=[doc.get(config.ID_FIELD) for doc in docs])

    def on_update(self, updates, original):
        updates["user_id"] = get_user_id()

    def on_updated(self, updates, original):
        """
        Send notifification
        :param updates:
        :param original:
        :return:
        """
        push_notification("system_message:updated", _id=[original.get(config.ID_FIELD)])

    def on_deleted(self, doc):
        """
        Send a notification
        :param doc:
        :return:
        """
        push_notification("system_message:deleted", _id=[doc.get(config.ID_FIELD)])

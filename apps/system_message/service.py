# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from flask import current_app as app
from superdesk.services import Service
from superdesk.notification import push_notification
from superdesk.errors import SuperdeskApiError
from apps.auth import is_current_user_admin
from flask_babel import _
from eve.utils import config


class SystemMessagesService(Service):
    def on_create(self, docs):
        for doc in docs:
            self._validate_administrator("create")
            self._validate_message(doc)

    def on_created(self, docs):
        """
        Send notification
        :param docs:
        :return:
        """
        push_notification("system_message:created", _id=[doc.get(config.ID_FIELD) for doc in docs])

    def on_update(self, updates, original):
        self._validate_administrator("update")

    def on_updated(self, updates, original):
        """
        Send notifification
        :param updates:
        :param original:
        :return:
        """
        push_notification("system_message:updated", _id=[original.get(config.ID_FIELD)])

    def on_delete(self, doc):
        self._validate_administrator("delete")

    def on_deleted(self, doc):
        """
        Send a notification
        :param doc:
        :return:
        """
        push_notification("system_message:deleted", _id=[doc.get(config.ID_FIELD)])

    def _validate_message(self, doc):
        max_characters = app.config.get("MAX_CHARACTERS_FOR_SYSTEM_MESSAGE", 200)
        if doc.get("message") and len(doc["message"]) > max_characters:
            raise SuperdeskApiError.badRequestError(
                message=_("Max {max_characters} characters are allowed").format(max_characters=max_characters)
            )

    def _validate_administrator(self, operation):
        if not is_current_user_admin():
            raise SuperdeskApiError.badRequestError(
                message=_("Only administrator user can {operation} the message").format(operation=operation)
            )

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core import get_current_app, get_app_config
from superdesk.resource import Resource
from superdesk.notification import push_notification
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from .user_mentions import get_users, get_desks, get_mentions, notify_mentioned_users, notify_mentioned_desks
from quart_babel import gettext as _

comments_schema = {
    "text": {
        "type": "string",
        "minlength": 1,
        "maxlength": 500,
        "required": True,
    },
    "item": {"type": "string"},
    "user": Resource.rel("users", True),
    "mentioned_users": {"type": "dict"},
    "mentioned_desks": {"type": "dict"},
}


class CommentsResource(Resource):
    """Reusable implementation for comments."""

    schema = comments_schema
    resource_methods = ["GET", "POST", "DELETE"]
    datasource = {"default_sort": [("_created", -1)]}
    privileges = {"POST": "archive", "DELETE": "archive"}


def encode_keys(doc, field):
    """Encode field keys before storing.

    Mongo doesn't allow `.` in dict key.

    :param doc: doc
    :param field: doc field
    """
    if not doc.get(field):
        return
    encoded = {}
    for key, val in doc.get(field).items():
        encoded[key.replace(".", ";")] = val
    doc[field] = encoded


def decode_keys(doc, field):
    """Decode encoded field keys.

    :param doc: doc
    :param field: doc field
    """
    if not doc.get(field):
        return
    decoded = {}
    for key, val in doc.get(field).items():
        decoded[key.replace(";", ".")] = val
    doc[field] = decoded


class CommentsService(BaseService):
    notification_key = "comments"
    notifications = True

    def on_create(self, docs):
        app = get_current_app()
        for doc in docs:
            sent_user = doc.get("user", None)
            user = app.get_current_user_dict()
            if sent_user and sent_user != str(user["_id"]):
                message = _("Commenting on behalf of someone else is prohibited.")
                raise SuperdeskApiError.forbiddenError(message)
            doc["user"] = user["_id"]
            user_names, desk_names = get_mentions(doc.get("text"))
            doc["mentioned_users"] = get_users(user_names)
            doc["mentioned_desks"] = get_desks(desk_names)
            encode_keys(doc, "mentioned_users")
            encode_keys(doc, "mentioned_desks")

    def on_fetched(self, doc):
        for item in doc.get("_items", []):
            decode_keys(item, "mentioned_users")
            decode_keys(item, "mentioned_desks")

    async def on_created(self, docs):
        for doc in docs:
            if self.notifications:
                push_notification(self.notification_key, item=str(doc.get("item")))
            decode_keys(doc, "mentioned_users")
            decode_keys(doc, "mentioned_desks")

        if self.notifications:
            # TODO-ASYNC: Support async (see superdesk.tests.markers.requires_eve_resource_async_event)
            await notify_mentioned_users(docs, get_app_config("CLIENT_URL", "").rstrip("/"))
            notify_mentioned_desks(docs)

    def on_updated(self, updates, original):
        push_notification(self.notification_key, updated=1)

    def on_deleted(self, doc):
        push_notification(self.notification_key, deleted=1)

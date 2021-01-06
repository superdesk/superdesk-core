# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service, editor_utils
from superdesk.media.crop import CropService
from superdesk.metadata.item import ITEM_STATE, EMBARGO, SCHEDULE_SETTINGS
from superdesk.utc import utcnow
from superdesk.text_utils import update_word_count
from apps.archive.common import set_sign_off, ITEM_OPERATION, get_user
from apps.archive.archive import flush_renditions
from apps.tasks import send_to
from apps.auth import get_user_id
from .common import BasePublishService, BasePublishResource, ITEM_CORRECT
from superdesk.emails import send_translation_changed
from superdesk.activity import add_activity
from flask import g, current_app as app


def send_translation_notifications(original):
    translated_items = get_resource_service("published").find(
        {"translation_id": original.get("guid"), "last_published_version": True}
    )

    user_ids = set()
    for translated_item in translated_items:
        if translated_item.get("item_id") == original.get("_id"):
            changed_article = translated_item
            continue
        user_ids.add(translated_item.get("original_creator"))
        user_ids.add(translated_item.get("version_creator"))

    if len(user_ids) == 0 or changed_article is None:
        return

    add_activity("translated:changed", "", resource=None, item=changed_article, notify=user_ids)

    recipients = []
    for user_id in user_ids:
        user = get_resource_service("users").find_one(req=None, _id=user_id)
        if user is not None and user.get("email", None) is not None:
            recipients.append(user.get("email"))

    if len(recipients) == 0:
        return

    username = g.user.get("display_name") or g.user.get("username")
    send_translation_changed(username, changed_article, recipients)


class CorrectPublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, "correct")


class CorrectPublishService(BasePublishService):
    publish_type = "correct"
    published_state = "corrected"
    item_operation = ITEM_CORRECT

    def set_state(self, original, updates):
        updates[ITEM_STATE] = self.published_state

        if original.get(EMBARGO) or updates.get(EMBARGO):
            # embargo time elapsed
            utc_embargo = updates.get(SCHEDULE_SETTINGS, {}).get("utc_{}".format(EMBARGO)) or original.get(
                SCHEDULE_SETTINGS, {}
            ).get("utc_{}".format(EMBARGO))
            if utc_embargo and utc_embargo < utcnow():
                # remove embargo information. so the next correction is without embargo.
                updates[EMBARGO] = None
                super().set_state(original, updates)
        else:
            super().set_state(original, updates)

    def change_being_corrected_to_published(self, updates, original):
        if app.config.get("CORRECTIONS_WORKFLOW") and original.get("state") == "correction":
            publish_service = get_resource_service("published")
            being_corrected_article = publish_service.find_one(
                req=None, guid=original.get("guid"), state="being_corrected"
            )

            if being_corrected_article.get("correction_sequence", 0) > 0:
                publish_service.patch(being_corrected_article["_id"], updates={"state": "corrected"})
            else:
                publish_service.patch(being_corrected_article["_id"], updates={"state": "published"})

    def send_to_original_desk(self, updates, original):
        if (
            app.config.get("CORRECTIONS_WORKFLOW")
            and original.get("state") == "correction"
            and original.get("task", {}).get("desk_history")
        ):
            send_to(
                doc=updates,
                desk_id=(original["task"]["desk_history"][0]),
                default_stage="working_stage",
                user_id=get_user_id(),
            )

    def on_update(self, updates, original):
        CropService().validate_multiple_crops(updates, original)
        super().on_update(updates, original)
        updates[ITEM_OPERATION] = self.item_operation
        updates["versioncreated"] = utcnow()
        updates["correction_sequence"] = original.get("correction_sequence", 1) + 1
        set_sign_off(updates, original)
        update_word_count(updates, original)
        flush_renditions(updates, original)
        self.change_being_corrected_to_published(updates, original)
        self.send_to_original_desk(updates, original)

    def update(self, id, updates, original):
        editor_utils.generate_fields(updates)
        get_resource_service("archive")._handle_media_updates(updates, original, get_user())
        super().update(id, updates, original)

    def on_updated(self, updates, original):
        super().on_updated(updates, original)
        send_translation_notifications(original)

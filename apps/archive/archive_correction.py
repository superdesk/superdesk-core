# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from apps.auth import get_user
from flask import request, current_app as app
from superdesk import get_resource_service, Service, config
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, metadata_schema
from superdesk.resource import Resource
from apps.archive.common import ARCHIVE, ITEM_CANCEL_CORRECTION, ITEM_CORRECTION
from superdesk.metadata.utils import item_url
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.notification import push_notification
from flask_babel import _

logger = logging.getLogger(__name__)


class ArchiveCorrectionResource(Resource):
    endpoint_name = "archive_correction"
    resource_title = endpoint_name

    schema = metadata_schema.copy()

    datasource = {
        "source": "archive",
    }
    item_url = item_url
    url = "archive/correction"
    resource_methods = []
    item_methods = ["PATCH"]
    privileges = {"PATCH": "correct"}


class ArchiveCorrectionService(Service):
    def on_update(self, updates, original):
        remove_correction = request.args.get("remove_correction") == "true"
        self._validate_correction(original)
        archive_service = get_resource_service(ARCHIVE)
        published_service = get_resource_service("published")
        archive_item = archive_service.find_one(req=None, _id=original.get(config.ID_FIELD))

        if remove_correction:
            published_article = published_service.find_one(
                req=None, guid=original.get("guid"), state=CONTENT_STATE.BEING_CORRECTED
            )

        elif original.get("state") == CONTENT_STATE.CORRECTED:
            published_article = published_service.find_one(
                req=None,
                guid=original.get("guid"),
                correction_sequence=original.get("correction_sequence"),
                state=CONTENT_STATE.CORRECTED,
            )
        else:
            published_article = published_service.find_one(req=None, guid=original.get("guid"))

        # updates for item in archive.
        if not remove_correction:
            archive_item_updates = {ITEM_STATE: CONTENT_STATE.CORRECTION, "operation": CONTENT_STATE.CORRECTION}
        elif remove_correction and archive_item.get("correction_sequence"):
            archive_item_updates = {ITEM_STATE: CONTENT_STATE.CORRECTED, "operation": ITEM_CANCEL_CORRECTION}
        else:
            archive_item_updates = {ITEM_STATE: CONTENT_STATE.PUBLISHED, "operation": ITEM_CANCEL_CORRECTION}

        # updates for item in published.
        if not remove_correction:
            published_item_updates = {
                ITEM_STATE: CONTENT_STATE.BEING_CORRECTED,
                "operation": CONTENT_STATE.BEING_CORRECTED,
            }
        elif remove_correction and published_article.get("correction_sequence"):
            published_item_updates = {ITEM_STATE: CONTENT_STATE.CORRECTED, "operation": "correct"}
        else:
            published_item_updates = {ITEM_STATE: CONTENT_STATE.PUBLISHED, "operation": ITEM_CANCEL_CORRECTION}

        # clear publishing schedule when we create correction
        if archive_item.get("publish_schedule"):
            archive_item_updates.update({"publish_schedule": None, "schedule_settings": {}})

        # modify item in archive.
        archive_service.system_update(archive_item.get(config.ID_FIELD), archive_item_updates, archive_item)
        app.on_archive_item_updated(archive_item_updates, archive_item, ITEM_CORRECTION)

        # modify item in published.
        published_service.patch(id=published_article.get(config.ID_FIELD), updates=published_item_updates)

        user = get_user(required=True)
        push_notification("item:correction", item=original.get(config.ID_FIELD), user=str(user.get(config.ID_FIELD)))

    def _validate_correction(self, original):
        """Validates the article to be corrected.

        :param original: article to be corrected.
        :raises: SuperdeskApiError
        """
        if not original:
            raise SuperdeskApiError.notFoundError(message=_("Cannot find the article"))

        if (
            not is_workflow_state_transition_valid("correction", original[ITEM_STATE])
            and not config.ALLOW_UPDATING_SCHEDULED_ITEMS
        ):
            raise InvalidStateTransitionError()

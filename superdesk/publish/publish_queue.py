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
from typing import Dict, Any

from superdesk import get_resource_service
from superdesk.notification import push_notification
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.utils import SuperdeskBaseEnum
from flask import current_app as app

logger = logging.getLogger(__name__)


PUBLISHED_IN_PACKAGE = "published_in_package"


class QueueState(SuperdeskBaseEnum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    RETRYING = "retrying"
    SUCCESS = "success"
    CANCELED = "canceled"
    ERROR = "error"
    FAILED = "failed"


class PublishQueueResource(Resource):
    schema = {
        "item_id": {"type": "string", "required": True},
        "item_version": {"type": "integer", "nullable": False},
        "formatted_item": {"type": "string", "nullable": False},
        "item_encoding": {"type": "string", "nullable": True},
        "encoded_item_id": {"type": "objectid", "nullable": True},
        "subscriber_id": Resource.rel("subscribers"),
        "codes": {"type": "list", "nullable": True},
        "destination": {
            "type": "dict",
            "schema": {
                "name": {"type": "string", "required": True, "empty": False},
                "format": {"type": "string", "required": True},
                "delivery_type": {"type": "string", "required": True},
                "config": {"type": "dict"},
            },
        },
        PUBLISHED_IN_PACKAGE: {"type": "string"},
        "published_seq_num": {"type": "integer"},
        # publish_schedule is to indicate the item schedule datetime.
        # entries in the queue are created after schedule has elapsed.
        "publish_schedule": {"type": "datetime"},
        "publishing_action": {"type": "string"},
        "unique_name": {"type": "string", "nullable": True},
        "content_type": {"type": "string"},
        "headline": {"type": "string", "nullable": True},
        "transmit_started_at": {"type": "datetime"},
        "completed_at": {"type": "datetime"},
        "state": {"type": "string", "allowed": QueueState.values(), "nullable": False},
        "error_message": {"type": "string"},
        # to indicate the queue item is moved to legal
        # True is set after state of the item is success, cancelled or failed. For other state it is false
        "moved_to_legal": {"type": "boolean", "default": False},
        "retry_attempt": {"type": "integer", "default": 0},
        "next_retry_attempt_at": {"type": "datetime"},
        "ingest_provider": Resource.rel("ingest_providers", nullable=True),
        "associated_items": {"type": "list", "nullable": True},
        "priority": {
            "type": "boolean",
            "nullable": True,
        },
    }

    additional_lookup = {"url": r'regex("[\w,.:-]+")', "field": "item_id"}

    etag_ignore_fields = ["moved_to_legal"]
    datasource: Dict[str, Any] = {"default_sort": [("_id", -1), ("subscriber_id", 1), ("published_seq_num", -1)]}
    privileges = {"POST": "publish_queue", "PATCH": "publish_queue"}


class PublishQueueService(BaseService):
    def on_create(self, docs):
        subscriber_service = get_resource_service("subscribers")

        for doc in docs:
            self._set_queue_state(doc, {})
            doc["moved_to_legal"] = False

            if "published_seq_num" not in doc:
                subscriber = subscriber_service.find_one(req=None, _id=doc["subscriber_id"])
                doc["published_seq_num"] = subscriber_service.generate_sequence_number(subscriber)

    def on_updated(self, updates, original):
        if updates.get("state", "") != original.get("state", ""):
            self._set_queue_state(updates, original)
            push_notification(
                "publish_queue:update",
                queue_id=str(original["_id"]),
                completed_at=(updates.get("completed_at").isoformat() if updates.get("completed_at") else None),
                state=updates.get("state"),
                error_message=updates.get("error_message"),
            )

    def _set_queue_state(self, updates, original):
        destination = updates.get("destination", original.get("destination")) or {}
        updates["state"] = (
            QueueState.SUCCESS.value
            if destination.get("delivery_type") == "content_api"
            else updates.get("state") or QueueState.PENDING.value
        )

    def delete(self, lookup):
        # as encoded item is added manually to storage
        # we also need to remove it manually on delete
        cur = self.get_from_mongo(req=None, lookup=lookup).sort("_id", 1)
        for doc in cur:
            try:
                encoded_item_id = doc["encoded_item_id"]
            except KeyError:
                pass
            else:
                app.storage.delete(encoded_item_id)
        return super().delete(lookup)

    def delete_by_article_id(self, _id):
        lookup = {"item_id": _id}
        self.delete(lookup=lookup)

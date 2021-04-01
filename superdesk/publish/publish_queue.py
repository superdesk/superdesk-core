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
import json
from typing import Dict, Any

from superdesk import config
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

    def create(self, docs, **kwargs):
        super().create(docs)

        is_publish = kwargs.get("is_publish")
        if not is_publish and not app.config.get("PUBLISH_ASSOCIATIONS_RESEND") == "never":
            for doc in docs:
                if app.config.get("PUBLISH_ASSOCIATIONS_RESEND") == "corrections":
                    self.resend_association_items(doc)
                elif app.config.get("PUBLISH_ASSOCIATIONS_RESEND") == "updates" and not self.is_corrected_document(doc):
                    self.resend_association_items(doc)
                elif not (self.is_corrected_document(doc) or self.is_updated_document(doc)):
                    self.resend_association_items(doc)

        return [doc[config.ID_FIELD] for doc in docs]

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

    def is_updated_document(self, doc):
        if not doc.get("item_id"):
            return
        article = get_resource_service("published").find_one(req=None, guid=doc["item_id"])
        if not article:
            return
        return article.get("rewrite_of")

    def is_corrected_document(self, doc):
        if not doc.get("item_id"):
            return
        article = get_resource_service("published").find_one(req=None, guid=doc["item_id"])
        if not article:
            return
        return doc.get("publishing_action") == "corrected" or article.get("operation") == "being_corrected"

    def resend_association_items(self, doc):
        associated_items = doc.get("associated_items")

        if associated_items:
            for id in associated_items:
                archive_article = get_resource_service("archive").find_one(req=None, _id=id)
                associated_article = get_resource_service("published").find_one(
                    req=None, guid=archive_article.get("guid")
                )
                subscriber = get_resource_service("subscribers").find_one(req=None, _id=doc["subscriber_id"])
                if associated_article and subscriber:
                    from apps.publish.enqueue import get_enqueue_service

                    get_enqueue_service(associated_article.get("operation")).queue_transmission(
                        associated_article, [subscriber]
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

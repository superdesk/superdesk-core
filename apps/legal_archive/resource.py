# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.archive.resource import ArchiveResource, ArchiveVersionsResource
from apps.archive_history import ArchiveHistoryResource

from typing import Any

from superdesk.types import PublishQueueState
from superdesk.resource import Resource
from superdesk.metadata.item import get_schema
from superdesk.mongo import TEXT_INDEX_OPTIONS
from superdesk.publish import PUBLISHED_IN_PACKAGE


LEGAL_ARCHIVE_NAME = "legal_archive"
LEGAL_ARCHIVE_VERSIONS_NAME = "legal_archive_versions"
LEGAL_ARCHIVE_HISTORY_NAME = "legal_archive_history"
LEGAL_PUBLISH_QUEUE_NAME = "legal_publish_queue"


class LegalResource(Resource):
    resource_methods = ["GET"]
    item_methods = ["GET"]
    privileges = {"GET": LEGAL_ARCHIVE_NAME}
    mongo_prefix = "LEGAL_ARCHIVE"
    schema = get_schema()


class LegalArchiveResource(LegalResource, ArchiveResource):
    endpoint_name = LEGAL_ARCHIVE_NAME
    resource_title = endpoint_name
    schema = get_schema()
    datasource = {"source": LEGAL_ARCHIVE_NAME}
    versioning = True
    mongo_indexes = ArchiveResource.mongo_indexes.copy()  # type: Any
    mongo_indexes.update(
        {
            "text": (
                [
                    ("headline", "text"),
                    ("slugline", "text"),
                    ("description_text", "text"),
                ],
                TEXT_INDEX_OPTIONS,
            ),
        }
    )


class LegalArchiveVersionsResource(LegalResource, ArchiveVersionsResource):
    endpoint_name = LEGAL_ARCHIVE_VERSIONS_NAME
    resource_title = endpoint_name
    schema = get_schema(versioning=True)
    datasource = {"source": LEGAL_ARCHIVE_VERSIONS_NAME, "projection": {"old_version": 0, "last_version": 0}}


class LegalArchiveHistoryResource(LegalResource, ArchiveHistoryResource):
    endpoint_name = LEGAL_ARCHIVE_HISTORY_NAME
    resource_title = endpoint_name
    schema = get_schema()
    schema.update(
        {
            "update": {"type": "dict", "schema": {}},
        }
    )
    datasource = {"source": LEGAL_ARCHIVE_HISTORY_NAME}
    mongo_indexes = {"item_id": ([("item_id", 1)], {"background": True})}


class LegalPublishQueueResource(LegalResource):
    endpoint_name = LEGAL_PUBLISH_QUEUE_NAME
    resource_title = endpoint_name

    additional_lookup = {"url": r'regex("[\w,.:-]+")', "field": "item_id"}
    etag_ignore_fields = ["moved_to_legal"]
    collation = False
    notifications = False

    schema = {
        # Copied from old PublishQueue eve resource
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
        "state": {"type": "string", "allowed": [qs.value for qs in PublishQueueState], "nullable": False},
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
        "_subscriber_id": Resource.rel("subscribers"),
    }

    datasource = {"source": LEGAL_PUBLISH_QUEUE_NAME}

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.archive.archive import ArchiveResource, ArchiveVersionsResource
from apps.archive_history import ArchiveHistoryResource

from typing import Any
from superdesk.publish.publish_queue import PublishQueueResource
from superdesk.resource import Resource
from superdesk.metadata.item import get_schema
from superdesk.mongo import TEXT_INDEX_OPTIONS


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


class LegalPublishQueueResource(LegalResource, PublishQueueResource):
    endpoint_name = LEGAL_PUBLISH_QUEUE_NAME
    resource_title = endpoint_name

    item_schema = {"_subscriber_id": Resource.rel("subscribers")}
    item_schema.update(PublishQueueResource.schema)
    schema = item_schema

    datasource = {"source": LEGAL_PUBLISH_QUEUE_NAME}

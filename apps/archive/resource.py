# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.archive.common import item_schema
from superdesk.metadata.item import PROCESSED_FROM
from superdesk.resource import Resource
from superdesk.metadata.utils import (
    extra_response_fields,
    item_url,
    aggregations,
    get_elastic_highlight_query,
)
from .common import ARCHIVE as SOURCE
from .utils import private_content_filter


class ArchiveResource(Resource):
    schema = item_schema()
    extra_response_fields = extra_response_fields
    item_url = item_url
    datasource = {
        "search_backend": "elastic",
        "aggregations": aggregations,
        "es_highlight": get_elastic_highlight_query,
        "projection": {"old_version": 0, "last_version": 0},
        "default_sort": [("_updated", -1)],
        "elastic_filter": {
            "bool": {
                "must": {
                    "terms": {
                        "state": [
                            "draft",
                            "fetched",
                            "routed",
                            "in_progress",
                            "spiked",
                            "submitted",
                            "unpublished",
                            "correction",
                        ]
                    }
                },
                "must_not": {"term": {"version": 0}},
            }
        },
        "elastic_filter_callback": private_content_filter,
    }
    etag_ignore_fields = ["broadcast"]
    resource_methods = ["GET", "POST"]
    item_methods = ["GET", "PATCH", "PUT"]
    versioning = True
    privileges = {"POST": SOURCE, "PATCH": SOURCE, "PUT": SOURCE}
    collation = False
    mongo_indexes = {
        "uri_1": ([("uri", 1)], {"background": True}),
        "ingest_id_1": ([("ingest_id", 1)], {"background": True}),
        "unique_id_1": ([("unique_id", 1)], {"background": True}),
        "processed_from_1": ([(PROCESSED_FROM, 1)], {"background": True}),
        "assignment_id_1": ([("assignment_id", 1)], {"background": True}),
    }


class ArchiveVersionsResource(Resource):
    schema = item_schema()
    schema.update(
        {
            "_id_document": Resource.not_analyzed_field(),
            "_current_version": Resource.field("integer"),
        }
    )
    extra_response_fields = extra_response_fields
    item_url = item_url
    resource_methods = []
    internal_resource = True
    privileges = {"PATCH": "archive"}
    collation = False
    versioning = False
    notifications = False
    mongo_indexes = {
        "guid": ([("guid", 1)], {"background": True}),
        "_id_document_1": ([("_id_document", 1)], {"background": True}),
    }

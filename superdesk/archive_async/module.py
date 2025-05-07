# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions, ElasticResourceConfig
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.types.archive import ArchiveResourceModel
from .service import AsyncArchiveService


archive_resource_config = ResourceConfig(
    name="archive",
    data_class=ArchiveResourceModel,
    service=AsyncArchiveService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="uri_1",
                keys=[("uri", 1), ("background", 1)],
                unique=False,
            ),
            MongoIndexOptions(
                name="ingest_id_1",
                keys=[("ingest_id", 1), ("background", 1)],
                unique=False,
            ),
            MongoIndexOptions(
                name="unique_id_1",
                keys=[("unique_id", 1), ("background", 1)],
                unique=False,
            ),
            MongoIndexOptions(
                name="processed_from_1",
                keys=[("processed_from", 1), ("background", 1)],
                unique=False,
            ),
            MongoIndexOptions(
                name="assignment_id_1",
                keys=[("assignment_id", 1), ("background", 1)],
                unique=False,
            ),
        ],
    ),
    elastic=ElasticResourceConfig(auto_create_index=False),
    # FIXME: To be activated at a later point.
    # rest_endpoints=RestEndpointConfig(
    #     item_methods=["GET", "PATCH", "PUT"],
    #     resource_methods=["GET", "POST"],
    #     enable_cors=True,
    # ),
)

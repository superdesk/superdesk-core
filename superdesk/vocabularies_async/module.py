# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.types import VocabulariesResourceModel
from .service import VocabulariesService


vocabularies_resource_config = ResourceConfig(
    name="vocabularies",
    data_class=VocabulariesResourceModel,
    service=VocabulariesService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="field_type",
                keys=[("field_type", 1)],
            ),
        ],
    ),
    rest_endpoints=RestEndpointConfig(
        item_methods=["GET", "PATCH", "DELETE"],
        resource_methods=["GET", "POST"],
    ),
)

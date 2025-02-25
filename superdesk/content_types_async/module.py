# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.types.content_types import ContentTypes
from .service import ContentTypesService


content_types_resource_config = ResourceConfig(
    name="content_types",
    data_class=ContentTypes,
    service=ContentTypesService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="label_1", keys=[("label", 1)], unique=True),
        ],
    ),
)

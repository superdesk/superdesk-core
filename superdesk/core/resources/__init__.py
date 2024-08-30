# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .model import Resources, ResourceModel, ResourceModelWithObjectId, ModelWithVersions, ResourceConfig, dataclass
from .resource_rest_endpoints import RestEndpointConfig
from .service import AsyncResourceService
from ..mongo import MongoResourceConfig, MongoIndexOptions
from ..elastic.resources import ElasticResourceConfig

__all__ = [
    "Resources",
    "ResourceModel",
    "ResourceModelWithObjectId",
    "ModelWithVersions",
    "ResourceConfig",
    "dataclass",
    "fields",
    "RestEndpointConfig",
    "AsyncResourceService",
    "MongoResourceConfig",
    "MongoIndexOptions",
    "ElasticResourceConfig",
]

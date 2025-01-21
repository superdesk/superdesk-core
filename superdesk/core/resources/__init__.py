# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core.types import MongoResourceConfig, MongoIndexOptions, ElasticResourceConfig
from .utils import get_projection_from_request
from .model import (
    BaseModel,
    ResourceModel,
    ResourceModelWithObjectId,
    ModelWithVersions,
    dataclass,
    Dataclass,
    default_model_config,
)
from .resource_config import ResourceConfig
from .resource_manager import Resources
from .resource_rest_endpoints import RestEndpointConfig, RestParentLink, get_id_url_type
from .service import AsyncResourceService, AsyncCacheableService
from .resource_signals import global_signals

__all__ = [
    "get_projection_from_request",
    "BaseModel",
    "Resources",
    "ResourceModel",
    "ResourceModelWithObjectId",
    "ModelWithVersions",
    "ResourceConfig",
    "dataclass",
    "fields",
    "RestEndpointConfig",
    "RestParentLink",
    "get_id_url_type",
    "AsyncResourceService",
    "AsyncCacheableService",
    "MongoResourceConfig",
    "MongoIndexOptions",
    "ElasticResourceConfig",
    "global_signals",
]

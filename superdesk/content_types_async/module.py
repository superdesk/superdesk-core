# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.content_types.content_types import CONTENT_TYPE_PRIVILEGE
from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.core.resources.resource_rest_endpoints import RestEndpointConfig
from superdesk.types import ContentTypesResourceModel
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules

from .service import ContentTypesService


content_types_resource_config = ResourceConfig(
    name="content_types",
    data_class=ContentTypesResourceModel,
    service=ContentTypesService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(name="label_1", keys=[("label", 1)], unique=True),
        ],
    ),
    default_sort=[("priority", -1)],
    # rest_endpoints=RestEndpointConfig(
    #     id_param_type=r'regex("[\w,.:-]+")',
    #     auth=http_method_privilege_based_rules(
    #         {
    #             "POST": CONTENT_TYPE_PRIVILEGE,
    #             "PATCH": CONTENT_TYPE_PRIVILEGE,
    #             "DELETE": CONTENT_TYPE_PRIVILEGE,
    #         }
    #     ),
    # ),
)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from apps.search_providers.registry import (
    registered_search_providers,
    allowed_search_providers,
    register_search_provider,
)  # noqa
from apps.search_providers.resource import SearchProviderResource
from apps.search_providers.service import SearchProviderService
from apps.search_providers.registry import SearchProviderAllowedResource, SearchProviderAllowedService


def init_app(app):
    from apps.search_providers.proxy import SearchProviderProxyResource, SearchProviderProxyService

    superdesk.privilege(
        name="search_providers", label="Manage Search Providers", description="User can manage search providers."
    )

    superdesk.register_resource(name="search_providers", resource=SearchProviderResource, service=SearchProviderService)

    superdesk.register_resource(
        name="search_providers_proxy", resource=SearchProviderProxyResource, service=SearchProviderProxyService
    )

    superdesk.register_resource(
        name="search_providers_allowed", resource=SearchProviderAllowedResource, service=SearchProviderAllowedService
    )

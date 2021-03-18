# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any
from flask_babel import lazy_gettext
import superdesk
from superdesk import get_backend

from apps.content_filters.filter_condition.filter_condition_resource import FilterConditionResource
from apps.content_filters.filter_condition.filter_condition_service import FilterConditionService
from apps.content_filters.content_filter.content_filter_resource import ContentFilterResource
from apps.content_filters.content_filter.content_filter_service import ContentFilterService

from apps.content_filters.filter_condition.filter_condition_parameters import (
    FilterConditionParametersResource,
    FilterConditionParametersService,
)

from apps.content_filters.content_filter.content_filter_test import ContentFilterTestResource, ContentFilterTestService


def init_app(app) -> None:
    endpoint_name = "filter_conditions"
    service: Any = FilterConditionService(endpoint_name, backend=get_backend())
    FilterConditionResource(endpoint_name, app=app, service=service)

    endpoint_name = "filter_condition_parameters"
    service = FilterConditionParametersService(endpoint_name, backend=get_backend())
    FilterConditionParametersResource(endpoint_name, app=app, service=service)

    endpoint_name = "content_filters"
    service = ContentFilterService(endpoint_name, backend=get_backend())
    ContentFilterResource(endpoint_name, app=app, service=service)

    endpoint_name = "content_filter_tests"
    service = ContentFilterTestService(endpoint_name, backend=superdesk.get_backend())
    ContentFilterTestResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="content_filters",
        label=lazy_gettext("Content Filters"),
        description=lazy_gettext("User can manage content filters"),
    )

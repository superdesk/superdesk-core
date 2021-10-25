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
from apps.products.resource import ProductsResource
from apps.products.service import ProductsService
from apps.products.product_test import ProductTestService, ProductTestResource


def init_app(app) -> None:
    endpoint_name = "products"
    service: Any = ProductsService(endpoint_name, backend=get_backend())
    ProductsResource(endpoint_name, app=app, service=service)

    endpoint_name = "product_tests"
    service = ProductTestService(endpoint_name, backend=superdesk.get_backend())
    ProductTestResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="products",
        label=lazy_gettext("Products Management"),
        description=lazy_gettext("User can manage product lists."),
    )

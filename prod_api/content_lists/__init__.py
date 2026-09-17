# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from .service import ContentListsService, ContentListItemsService
from .resource import ContentListsResource, ContentListItemsResource


def init_app(app) -> None:
    """Initialize the `content_lists` and `content_lists/<list_id>/items` API endpoints.

    :param app: the API application object
    :type app: `Eve`
    """
    lists_service = ContentListsService(datasource="content_lists", backend=superdesk.get_backend())
    ContentListsResource(endpoint_name="content_lists", app=app, service=lists_service)

    items_service = ContentListItemsService(datasource="content_list_items", backend=superdesk.get_backend())
    ContentListItemsResource(endpoint_name="content_list_items", app=app, service=items_service)

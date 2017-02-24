# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from content_api.items.resource import ItemsResource


class PackagesResource(ItemsResource):
    """A class defining and configuring the /packages API endpoint."""

    datasource = {
        'source': 'items',
        'search_backend': 'elastic',
        'elastic_filter': {"bool": {"must": {"term": {"type": "composite"}}}},
        'default_sort': [('_updated', -1)],
    }
    item_methods = ['GET']
    resource_methods = ['GET']

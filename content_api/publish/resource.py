# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from content_api import MONGO_PREFIX, ELASTIC_PREFIX
from content_api.items.resource import schema as item_schema
from copy import deepcopy


class PublishResource(Resource):
    """A class defining and configuring the /publish API endpoint."""

    schema = deepcopy(item_schema)

    datasource = {
        'source': 'items',
        'search_backend': 'elastic',
    }

    mongo_prefix = MONGO_PREFIX
    elastic_prefix = ELASTIC_PREFIX

    item_methods = []
    resource_methods = []

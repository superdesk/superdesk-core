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

from content_api.items.resource import schema
from copy import copy


class PublishResource(Resource):
    """A class defining and configuring the /publish API endpoint."""

    # Example of an ID of an object in database (whitout quotes):
    #
    #     "tag:example.com,0000:newsml_BRE9A605"
    #     "tag:localhost:2015:f4b35e12-559b-4a2b-b1f2-d5e64048bde8"
    #
    item_url = 'regex("[\w,.:-]+")'
    schema = copy(schema)
    schema.update(guid={'type': 'string', 'required': True})

    datasource = {
        'source': 'items',
        'search_backend': 'elastic',
    }

    item_methods = ['GET']
    resource_methods = ['POST']

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from content_api import MONGO_PREFIX


class CompanyTokenResource(Resource):
    schema = {
        '_id': {'type': 'string', 'unique': True},
        'expiry': {'type': 'datetime'},
        'company': Resource.rel('companies', required=False),
    }

    item_url = 'regex(".+")'
    resource_methods = ['GET', 'POST']
    item_methods = ['GET', 'DELETE']
    privileges = {'POST': 'subscribers', 'DELETE': 'subscribers'}

    datasource = {
        'default_sort': [('_created', 1)],
    }

    mongo_prefix = MONGO_PREFIX

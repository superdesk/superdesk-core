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


class ProfilingResource(Resource):
    """
    Profiling schema
    """

    schema = {
        'name': {'type': 'string', 'required': True, 'unique': True},
        'profiling_data': {'type': 'list', 'required': True}
    }
    item_url = 'regex("[\w,.:-]+")'
    item_methods = ['GET']
    resource_methods = ['GET', 'POST', 'DELETE']
    privileges = {'POST': 'profiling', 'DELETE': 'profiling'}

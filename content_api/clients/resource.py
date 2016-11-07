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


class ClientsResource(Resource):
    """
    Clients schema
    """

    schema = {
        'name': {
            'type': 'string',
            'unique': True,
            'required': True
        },
        'client_type': {
            'type': 'string',
            'required': True
        }
    }
    item_methods = ['GET', 'PATCH', 'PUT']
    resource_methods = ['GET', 'POST']

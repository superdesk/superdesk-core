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


class TokensResource(Resource):
    """
    Tokens schema
    """

    schema = {
        'client': Resource.rel('clients', True),
        'user': Resource.rel('users', True),
        'token_type': {'type': 'string', 'required': True},
        'access_token': {'type': 'string', 'required': True},
        'refresh_token': {'type': 'string', 'required': True},
        'expires': {'type': 'datetime', 'required': True},
    }
    item_methods = ['GET', 'PATCH', 'PUT', 'DELETE']
    resource_methods = ['GET', 'POST', 'DELETE']

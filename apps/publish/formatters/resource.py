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


class FormattersResource(Resource):
    """Formatters schema"""

    endpoint_name = 'formatters'
    resource_methods = ['GET', 'POST']
    item_methods = []
    resource_title = endpoint_name
    schema = {
        'name': {
            'type': 'string',
        },
        'article_id': {
            'type': 'string',
            'required': True
        },
        'formatter_name': {
            'type': 'string',
            'required': True
        }
    }
    privileges = {'POST': 'archive'}

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
from superdesk.metadata.utils import ProductTypes


class ProductsResource(Resource):
    """Products schema"""

    schema = {
        'name': {
            'type': 'string',
            'iunique': True,
            'required': True
        },
        'description': {
            'type': 'string'
        },
        'codes': {
            'type': 'string'
        },
        'content_filter': {
            'type': 'dict',
            'schema': {
                'filter_id': Resource.rel('content_filters', nullable=True),
                'filter_type': {
                    'type': 'string',
                    'allowed': ['blocking', 'permitting'],
                    'default': 'blocking'
                }
            },
            'nullable': True
        },
        'geo_restrictions': {
            'type': 'string',
            'nullable': True
        },
        'product_type': {
            'type': 'string',
            'default': ProductTypes.BOTH.value,
            'allowed': ProductTypes.values(),
            'required': True
        },
        'init_version': {'type': 'integer'},
    }

    privileges = {'POST': 'products', 'PATCH': 'products', 'DELETE': 'products'}

    mongo_indexes = {
        'name_1': ([('name', 1)], {'unique': True}),
    }

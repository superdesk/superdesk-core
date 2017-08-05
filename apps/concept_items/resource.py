# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource


CONCEPT_ITEMS_PRIVILEGE = 'concept_items'


class ConceptItemResource(Resource):
    schema = {
        'first_name': {
            'type': 'string',
            'required': True
        },
        'last_name': {
            'type': 'string',
            'required': True
        },
        'by_line': {
            'type': 'string'
        },
        'email': {
            'type': 'string'
        },
        'biography': {
            'type': 'string'
        },
        'role': {
            'type': 'string'
        }
    }
    resource_methods = ['GET', 'POST', 'DELETE']
    item_methods = ['GET', 'PATCH', 'PUT', 'DELETE']
    privileges = {'GET': CONCEPT_ITEMS_PRIVILEGE, 'POST': CONCEPT_ITEMS_PRIVILEGE,
                  'PATCH': CONCEPT_ITEMS_PRIVILEGE, 'PUT': CONCEPT_ITEMS_PRIVILEGE,
                  'DELETE': CONCEPT_ITEMS_PRIVILEGE}

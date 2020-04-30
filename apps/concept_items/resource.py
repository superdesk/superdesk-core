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

from .enums import ConceptNature


CONCEPT_ITEMS_PRIVELEGE = 'concept_items'


class ConceptItemsResource(Resource):
    """Concept item schema"""

    schema = {
        'name': {
            'type': 'string',
            'required': True,
            'empty': False
        },
        'group_id': {
            'type': 'string',
            'required': False,
            'empty': False,
            'readonly': False
        },
        'definition_text': {
            'type': 'string',
            'required': False,
            'empty': False,
            'readonly': True
        },
        'definition_html': {
            'type': 'string',
            'required': True,
            'empty': False
        },
        'language': {
            'type': 'string',
            'required': True,
            'empty': False
        },
        'labels': {
            'type': 'list',
            'schema': {
                'type': 'string'
            },
            'unique_list': True
        },
        # http://cv.iptc.org/newscodes/cpnature/
        'cpnat_type': {
            'type': 'string',
            'required': True,
            'allowed': ConceptNature.values()
        },
        # https://iptc.org/std/NewsML-G2/guidelines/#more-real-world-entities
        'properties': {
            'type': 'dict',
            'required': False
        },
        'created_by': Resource.rel('users', embeddable=False, readonly=True),
        'updated_by': Resource.rel('users', embeddable=False, readonly=True),
    }
    privileges = {
        'POST': CONCEPT_ITEMS_PRIVELEGE,
        'PATCH': CONCEPT_ITEMS_PRIVELEGE,
        'PUT': CONCEPT_ITEMS_PRIVELEGE,
        'DELETE': CONCEPT_ITEMS_PRIVELEGE
    }
    item_url = 'regex("[a-f0-9]{24}")'
    resource_methods = ['GET', 'POST']
    item_methods = ['GET', 'PATCH', 'PUT', 'DELETE']
    query_objectid_as_string = False
    mongo_indexes = {
        'name_collation': ([('name', 1)], {'collation': {'locale': 'en', 'strength': 1}}),
        'definition_text_collation': ([('definition_text', 1), ], {'collation': {'locale': 'en', 'strength': 1}}),
        'group_id': ([('group_id', 1), ('language', 1)], {'unique': True})
    }

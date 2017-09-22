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

CONCEPT_PRIVILEGE = 'concept'


class ConceptResource(Resource):
    """Resource class for concept items

    Each concept will have a type, for each defined type there will be a dictionary defined in the schema.

    """

    schema = {
        # distinguish what type of entity the concept item relates to
        'concept_type': {
            'type': 'string',
            'required': True
        },
        # flag to mark the concept item active/inactive for example if the item relates to a contact that is no longer
        # valid
        'is_active': {
            'type': 'boolean',
            'default': True
        },
        # flag to indicate that the concept item should not be publicly visible, for example if the item relates to
        # a contact that can not be distributed due to privacy concerns
        'public': {
            'type': 'boolean',
            'default': True
        },
        # schema that applies to the concept 'contact'
        'contact': {
            'type': 'dict',
            'schema': {
                'first_name': {
                    'type': 'string',
                    'required': False
                },
                'last_name': {
                    'type': 'string',
                    'required': False
                },
                'honorific': {
                    'type': 'string',
                    'required': False
                },
                'job_title': {
                    'type': 'string',
                    'required': False
                },
                'organisation': {
                    'type': 'string',
                    'required': False
                },
                'mobile': {
                    'type': 'list',
                    'schema': {
                            'type': 'dict',
                            'schema': {
                                'number': {'type': 'string'},
                                'usage': {'type': 'string'}
                            }
                    }
                },
                'phone': {
                    'type': 'list',
                    'schema': {
                        'type': 'dict',
                        'schema': {
                            'number': {'type': 'string'},
                            'usage': {'type': 'string'}
                        }
                    }
                },
                'fax': {
                    'type': 'string',
                    'required': False
                },
                'email': {
                    'type': 'list',
                    'required': False,
                    'schema': {
                        'type': 'string'
                    }
                },
                'twitter': {
                    'type': 'string',
                    'required': False
                },
                'facebook': {
                    'type': 'string',
                    'required': False
                },
                'instagram': {
                    'type': 'string',
                    'required': False
                },
                'website': {
                    'type': 'string',
                    'required': False
                },
                'address': {
                    'type': 'list',
                    'schema': {
                        'type': 'string',
                        'required': False
                    }
                },
                'locality': {
                    'type': 'string',
                    'required': False
                },
                'state': {
                    'type': 'string',
                    'required': False
                },
                'postcode': {
                    'type': 'string',
                    'required': False
                },
                'notes': {
                    'type': 'string',
                    'required': False
                }
            }
        }
    }

    datasource = {
        'source': 'concept',
        'search_backend': 'elastic'
    }

    url = 'concept/<regex("[\w]+"):concept_type>'
    item_url = 'regex("[\w]+")'
    privileges = {'POST': CONCEPT_PRIVILEGE,
                  'PATCH': CONCEPT_PRIVILEGE,
                  'DELETE': CONCEPT_PRIVILEGE}
    resource_title = 'concept'


# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource, text_with_keyword

CONTACTS_PRIVILEDGE = 'contacts'
VIEW_CONTACTS = 'view_contacts'


class ContactsResource(Resource):
    """Resource class for contact items

    A contact can either be for an individual or for an organisation

    """

    schema = {
        # flag to mark the contact item active/inactive for example if the item relates to a contact that is no longer
        # valid
        'is_active': {
            'type': 'boolean',
            'default': True
        },
        # flag to indicate that the contact item should not be publicly visible, for example if the item relates to
        # a contact that can not be distributed due to privacy concerns
        'public': {
            'type': 'boolean',
            'default': True
        },
        'organisation': {
            'type': 'string',
            'required': False,
            'mapping': text_with_keyword,
        },
        'first_name': {
            'type': 'string',
            'required': False,
            'mapping': text_with_keyword,
        },
        'last_name': {
            'type': 'string',
            'required': False,
            'mapping': text_with_keyword,
        },
        'honorific': {
            'type': 'string',
            'required': False
        },
        'job_title': {
            'type': 'string',
            'required': False
        },
        'mobile': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'number': {'type': 'string'},
                    # usage may provide information as to the usage of the number e.g. Business hours only
                    'usage': {'type': 'string'},
                    # If public is true then the number can be made public, if false it is only visible in the system
                    'public': {'type': 'boolean'}
                }
            }
        },
        'contact_phone': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'number': {'type': 'string'},
                    'usage': {'type': 'string'},
                    # If public is true then the number can be made public, if false it is only visible in the system
                    'public': {'type': 'boolean'}
                }
            }
        },
        'fax': {
            'type': 'string',
            'required': False
        },
        'contact_email': {
            'type': 'list',
            'required': False,
            'schema': {
                'type': 'email'
            }
        },
        'twitter': {
            'type': 'string',
            'required': False,
            'twitter': True
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
        'contact_address': {
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
        'city': {
            'type': 'string',
            'required': False
        },
        'contact_state': {
            'type': 'string',
            'required': False
        },
        'postcode': {
            'type': 'string',
            'required': False
        },
        'country': {
            'type': 'string',
            'required': False
        },
        'notes': {
            'type': 'string',
            'required': False
        },
        'contact_type': {
            'type': 'string',
            'required': False,
            'nullable': True,
        }
    }

    datasource = {
        'source': 'contacts',
        'search_backend': 'elastic'
    }
    item_url = r'regex("[\w]+")'
    privileges = {'POST': CONTACTS_PRIVILEDGE,
                  'PATCH': CONTACTS_PRIVILEDGE,
                  'DELETE': CONTACTS_PRIVILEDGE}


class OrganisationSearchResource(Resource):
    """Search for organisation within the contacts collection

    """

    datasource = {
        'source': 'contacts',
        'search_backend': 'elastic'
    }

    schema = ContactsResource.schema
    resource_methods = ['GET']
    item_methods = ['GET']
    url = 'contacts/organisations'
    resource_title = 'contacts_organisations'

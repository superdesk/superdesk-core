# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import cerberus
import superdesk
from bs4 import BeautifulSoup
from superdesk.metadata.item import ITEM_TYPE

logger = logging.getLogger(__name__)


def check_json(doc, field, value):
    if isinstance(doc, dict):
        if field in doc and doc[field] == value:
            return True
        for key in doc:
            if check_json(doc[key], field, value):
                return True
        return False
    elif isinstance(doc, list):
        for item in doc:
            if check_json(item, field, value):
                return True
        return False
    else:
        return False


class SchemaValidator(cerberus.Validator):
    def _validate_type_picture(self, field, value):
        """Allow type picture in schema."""
        pass

    def _validate_mandatory_in_list(self, mandatory, field, value):
        """Validates if all elements from mandatory are presented in the list"""
        for key in mandatory:
            for key_field in mandatory[key]:
                if not check_json(value, key, mandatory[key][key_field]):
                    self._error(key_field, 'is a required field')


class ValidateResource(superdesk.Resource):
    schema = {
        'act': {'type': 'string', 'required': True},
        'type': {'type': 'string', 'required': True},
        'validate': {
            'type': 'dict',
            'required': True
        }
    }

    resource_methods = ['POST']
    item_methods = []


class ValidateService(superdesk.Service):

    def create(self, docs, **kwargs):
        for doc in docs:
            doc['errors'] = self._validate(doc, **kwargs)

        return [doc['errors'] for doc in docs]

    def _get_validators(self, doc):
        """Get validators.

        In case there is profile defined for item with respective content type it will
        use its schema for validations, otherwise it will fall back to action/item_type filter.
        """
        profile = doc['validate'].get('profile')
        if profile:
            content_type = superdesk.get_resource_service('content_types').find_one(req=None, _id=profile)
            if content_type:
                return [content_type]
        lookup = {'act': doc['act'], 'type': doc[ITEM_TYPE]}
        return superdesk.get_resource_service('validators').get(req=None, lookup=lookup)

    def _sanitize_fields(self, doc, validator):
        '''
        If maxlength or minlength is specified in the validator then
        remove any markups from that field
        :param doc: Article to be validated
        :param validator: Validation rule
        :return: updated article
        '''
        fields_to_check = ['minlength', 'maxlength']
        schema = validator.get('schema', {})
        for field in schema:
            if doc.get(field) and any(k in schema[field] for k in fields_to_check):
                try:
                    doc[field] = BeautifulSoup(doc[field], 'html.parser').get_text()
                except TypeError:
                    # fails for json fields like subject, genre
                    pass

    def _validate(self, doc, **kwargs):
        lookup = {'act': doc['act'], 'type': doc[ITEM_TYPE]}
        use_headline = kwargs and 'headline' in kwargs
        validators = superdesk.get_resource_service('validators').get(req=None, lookup=lookup)
        validators = self._get_validators(doc)
        for validator in validators:
            self._sanitize_fields(doc['validate'], validator)
            v = SchemaValidator()
            v.allow_unknown = True
            v.validate(doc['validate'], validator['schema'])
            error_list = v.errors
            response = []
            for e in error_list:
                if error_list[e] == 'required field' or type(error_list[e]) is dict:
                    message = '{} is a required field'.format(e.upper())
                elif 'min length is 1' == error_list[e]:
                    message = '{} is a required field'.format(e.upper())
                elif 'min length is' in error_list[e]:
                    message = '{} is too short'.format(e.upper())
                elif 'max length is' in error_list[e]:
                    message = '{} is too long'.format(e.upper())
                else:
                    message = '{} {}'.format(e.upper(), error_list[e])

                if use_headline:
                    response.append('{}: {}'.format(doc['validate'].get('headline',
                                                                        doc['validate'].get('_id')), message))
                else:
                    response.append(message)
            return response
        else:
            return ['validator was not found for {}'.format(doc['act'])]

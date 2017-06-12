# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from eve.io.mongo import Validator
from superdesk.metadata.item import ITEM_TYPE
from superdesk.logging import logger
from superdesk.etree import get_text

REQUIRED_FIELD = 'is a required field'


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


def get_validator_schema(schema):
    """Get schema for given data that will work with validator.

    - if field is required without minlength set make sure it's not empty
    - if there are keys with None value - remove them

    :param schema
    """
    validator_schema = {key: val for key, val in schema.items() if val is not None}

    if validator_schema.get('required') and not validator_schema.get('minlength'):
        validator_schema.setdefault('empty', False)

    return validator_schema


class SchemaValidator(Validator):
    def _validate_type_picture(self, field, value):
        """Allow type picture in schema."""
        pass

    def _validate_mandatory_in_list(self, mandatory, field, value):
        """Validates if all elements from mandatory are presented in the list"""
        for key in mandatory:
            for key_field in mandatory[key]:
                if not check_json(value, key, mandatory[key][key_field]):
                    self._error(key_field, REQUIRED_FIELD)

    def _validate_mandatory_in_dictionary(self, mandatory, field, value):
        """Validates if all elements from mandatory are presented in the dictionary"""
        for key in mandatory:
            if not value.get(key):
                self._error(key, REQUIRED_FIELD)

    def _validate_empty(self, empty, field, value):
        """Original validates only strings, adding a list check."""
        super()._validate_empty(empty, field, value)
        if isinstance(value, list) and not value:
            self._error(field, REQUIRED_FIELD)

    def _validate_enabled(self, *args):
        """Ignore ``enabled`` in the schema."""
        pass

    def _validate_place(self, *args):
        """Ignore place."""
        pass

    def _validate_genre(self, *args):
        """Ignore genre."""
        pass

    def _validate_anpa_category(self, *args):
        """Ignore anpa category."""
        pass

    def _validate_subject(self, *args):
        """Ignore subject."""
        pass

    def _validate_company_codes(self, *args):
        """Ignore company codes."""
        pass


class ValidateResource(superdesk.Resource):
    schema = {
        'act': {'type': 'string', 'required': True},
        'type': {'type': 'string', 'required': True},
        'embedded': {'type': 'boolean', 'required': False},
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
        if profile and doc['act'] != 'auto_publish':
            # not use profile for auto publishing via routing.
            content_type = superdesk.get_resource_service('content_types').find_one(req=None, _id=profile)
            if content_type:
                return [content_type]
        lookup = {'act': doc['act'], 'type': doc[ITEM_TYPE]}
        if doc.get('embedded'):
            lookup['embedded'] = doc['embedded']
        else:
            lookup['$or'] = [{'embedded': {'$exists': False}}, {'embedded': False}]
        return superdesk.get_resource_service('validators').get(req=None, lookup=lookup)

    def _sanitize_fields(self, doc, validator):
        """If maxlength or minlength is specified in the validator then remove any markups from that field

        :param doc: Article to be validated
        :param validator: Validation rule
        :return: updated article
        """
        fields_to_check = ['minlength', 'maxlength']
        schema = validator.get('schema', {})
        for field in schema:
            if doc.get(field) and schema.get(field) and any(k in schema[field] for k in fields_to_check):
                try:
                    doc[field] = get_text(doc[field])
                except (ValueError, TypeError):
                    # fails for json fields like subject, genre
                    pass

    def _process_media(self, doc):
        """If feature media is required it should be present for validation on doc not only on associations
        If media_description is required it should be present for validation on doc not only on
        associations->featuremedia
        :param doc: Article to be validated
        """
        if 'associations' in doc and 'featuremedia' in doc['associations']:
            doc['feature_media'] = doc['associations']['featuremedia']
            if 'description_text' in doc['associations']['featuremedia']:
                doc['media_description'] = doc['associations']['featuremedia']['description_text']

    def _get_validator_schema(self, validator):
        """Get schema for given validator.

        And make sure there is no `None` value which would raise an exception.
        """
        return {field: get_validator_schema(schema) for field, schema in validator['schema'].items() if schema}

    def _validate(self, doc, **kwargs):
        use_headline = kwargs and 'headline' in kwargs
        validators = self._get_validators(doc)
        for validator in validators:
            self._sanitize_fields(doc['validate'], validator)
            self._process_media(doc['validate'])
            v = SchemaValidator()
            v.allow_unknown = True
            try:
                v.validate(doc['validate'], self._get_validator_schema(validator))
            except TypeError as e:
                logger.exception('Invalid validator schema value "%s" for ' % str(e))
            error_list = v.errors
            response = []
            for e in error_list:
                # Ignore dateline if item is corrected because it can't be changed after the item is published
                if doc.get('act', None) == 'correct' and e == 'dateline':
                    continue
                elif doc.get('act', None) == 'kill' and doc['validate'].get('profile', None) and \
                        e in ('headline', 'abstract', 'body_html'):
                    continue
                elif error_list[e] == 'required field' or type(error_list[e]) is dict or \
                        type(error_list[e]) is list:
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
            logger.warn('validator was not found for {}'.format(doc['act']))
            return []

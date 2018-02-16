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

from copy import deepcopy
from datetime import datetime
from flask import current_app as app
from eve.io.mongo import Validator
from superdesk.metadata.item import ITEM_TYPE
from superdesk.logging import logger
from superdesk.text_utils import get_text
from superdesk import get_resource_service

REQUIRED_FIELD = 'is a required field'
STRING_FIELD = 'require a string value'
DATE_FIELD = 'require a date value'
REQUIRED_ERROR = '{} is a required field'


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
    def _validate_type_media(self, field, value):
        """Allow type media in schema."""
        pass

    def _validate_type_embed(self, field, value):
        """Allow type media in schema."""
        pass

    def _validate_type_date(self, field, value):
        try:
            datetime.strptime(value or '', '%Y-%m-%dT%H:%M:%S+%f')
        except ValueError:
            self._error(field, DATE_FIELD)

    def _validate_type_picture(self, field, value):
        """Allow type picture in schema."""
        pass

    def _validate_type_text(self, field, value):
        """Validate type text in schema."""
        if value and not isinstance(value, str):
            self._error(field, STRING_FIELD)

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
        if isinstance(value, str) and value == '<p></p>':  # default value for editor3
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
            test_doc = deepcopy(doc)
            doc['errors'] = self._validate(test_doc, **kwargs)

        return [doc['errors'] for doc in docs]

    def _get_validators(self, doc):
        """Get validators.

        In case there is profile defined for item with respective content type it will
        use its schema for validations, otherwise it will fall back to action/item_type filter.
        """
        extra_field_types = {'text': 'string', 'embed': 'dict', 'date': 'date'}
        profile = doc['validate'].get('profile')
        if profile and doc['act'] != 'auto_publish':
            # not use profile for auto publishing via routing.
            content_type = superdesk.get_resource_service('content_types').find_one(req=None, _id=profile)
            if content_type:
                extra_fields = superdesk.get_resource_service('vocabularies').get_extra_fields()
                schema = content_type.get('schema', {})
                schema['extra'] = {'type': 'dict', 'schema': {}}
                doc['validate'].setdefault('extra', {})  # make sure extra is there so it will validate its fields
                for extra_field in extra_fields:
                    if schema.get(extra_field['_id']) and \
                            extra_field.get('field_type', None) in extra_field_types:
                        rules = schema.pop(extra_field['_id'])
                        rules['type'] = extra_field_types.get(extra_field['field_type'], 'string')
                        schema['extra']['schema'].update({extra_field['_id']: get_validator_schema(rules)})
                        self._populate_extra(doc['validate'], extra_field['_id'])
                content_type['schema'] = schema
                return [content_type]
        lookup = {'act': doc['act'], 'type': doc[ITEM_TYPE]}
        if doc.get('embedded'):
            lookup['embedded'] = doc['embedded']
        else:
            lookup['$or'] = [{'embedded': {'$exists': False}}, {'embedded': False}]
        custom_schema = app.config.get('SCHEMA', {}).get(doc[ITEM_TYPE])
        if custom_schema:
            return [{'schema': custom_schema}]
        return superdesk.get_resource_service('validators').get(req=None, lookup=lookup)

    def _populate_extra(self, doc, schema):
        """Populates the extra field in the document with fields stored in subject. Used
        for user defined vocabularies.

        :param doc: Article to be validated
        :param schema: Vocabulary identifier
        """
        for subject in doc.get('subject', []):
            if subject.get('scheme', '') == schema:
                doc['extra'][schema] = subject.get('qcode', '')

    def _sanitize_fields(self, doc, validator):
        """If maxlength or minlength is specified in the validator then remove any markups from that field

        :param doc: Article to be validated
        :param validator: Validation rule
        :return: updated article
        """
        fields_to_check = ['minlength', 'maxlength']
        item_schema = validator.get('schema', {})
        extra_schema = item_schema.get('extra', {}).get('schema', {})
        schemes_docs = [(item_schema, doc), (extra_schema, doc.get('extra', {}))]
        for schema, content in schemes_docs:
            for field in schema:
                if content.get(field) and schema.get(field) and type(content[field]) is str and \
                        any(k in schema[field] for k in fields_to_check):
                    try:
                        content[field] = get_text(content[field])
                    except (ValueError, TypeError):
                        # fails for json fields like subject, genre
                        pass

    def _get_media_field(self, field_schema, field_associations, doc,):
        """Returns the field name in associations. For multiple valued media fields
        the field asssociations name is different from the field schema name.
        :param field_schema: Field schema name
        :param field_associations: Field associations name
        :param doc: Article to be validated
        """
        if field_associations in doc.get('associations', {}):
            return field_associations
        media_multivalue_field = field_schema + '--'
        for media_field in doc.get('associations', {}):
            if media_field.startswith(media_multivalue_field):
                return media_field
        return None

    def _process_media(self, doc, validation_schema):
        """If media field(feature media or custom media field) is required it should be present for
        validation on doc not only on associations
        If media_description is required it should be present for validation on doc not only on
        associations->featuremedia (or custom media field)
        :param doc: Article to be validated
        :param schema: Schema to validate the article
        """
        for field_schema in validation_schema:
            field_associations = field_schema if field_schema != 'feature_media' else 'featuremedia'
            media_field = self._get_media_field(field_schema, field_associations, doc)
            if media_field:
                doc[field_schema] = doc['associations'][media_field]
                if not doc.get('feature_media', None) is None and 'description_text' in doc['feature_media']:
                    doc['media_description'] = doc['associations']['featuremedia']['description_text']

    def _process_sms(self, doc, schema):
        """Apply the SMS validation to the sms_message value if the document is flagged for SMS
        :param doc:
        :param schema:
        :return:
        """
        if doc.get('flags', {}).get('marked_for_sms', False):
            doc['sms'] = doc.get('sms_message', '')
        else:
            # remove it from the valiadation it is not required
            schema.pop('sms', None)

    def _get_validator_schema(self, validator):
        """Get schema for given validator.

        And make sure there is no `None` value which would raise an exception.
        """
        return {field: get_validator_schema(schema) for field, schema in validator['schema'].items() if schema}

    def _get_vocabulary_display_name(self, vocabulary_id):
        vocabulary = get_resource_service('vocabularies').find_one(req=None, _id=vocabulary_id)
        if vocabulary and 'display_name' in vocabulary:
            return vocabulary['display_name']
        return vocabulary_id

    def _set_default_subject_scheme(self, item):
        if item.get('subject'):
            for subject in item['subject']:
                subject.setdefault('scheme', None)

    def _validate(self, doc, **kwargs):
        use_headline = kwargs and 'headline' in kwargs
        validators = self._get_validators(doc)
        for validator in validators:
            validation_schema = self._get_validator_schema(validator)
            self._sanitize_fields(doc['validate'], validator)
            self._set_default_subject_scheme(doc['validate'])
            self._process_media(doc['validate'], validation_schema)
            self._process_sms(doc['validate'], validation_schema)
            v = SchemaValidator()
            v.allow_unknown = True
            try:
                v.validate(doc['validate'], validation_schema)
            except TypeError as e:
                logger.exception('Invalid validator schema value "%s" for ' % str(e))
            error_list = v.errors
            response = []
            for e in error_list:
                messages = []
                # Ignore dateline if item is corrected because it can't be changed after the item is published
                if doc.get('act', None) == 'correct' and e == 'dateline':
                    continue
                elif doc.get('act', None) == 'kill' and doc['validate'].get('profile', None) and \
                        e in ('headline', 'abstract', 'body_html'):
                    continue
                elif e == 'extra':
                    for field in error_list[e]:
                        display_name = self._get_vocabulary_display_name(field)
                        if 'required' in error_list[e][field]:
                            messages.append(REQUIRED_ERROR.format(display_name))
                        else:
                            messages.append('{} {}'.format(display_name, error_list[e][field]))
                elif error_list[e] == 'required field' or type(error_list[e]) is dict or \
                        type(error_list[e]) is list:
                    messages.append(REQUIRED_ERROR.format(e.upper()))
                elif 'min length is 1' == error_list[e] or 'null value not allowed' in error_list[e]:
                    messages.append(REQUIRED_ERROR.format(e.upper()))
                elif 'min length is' in error_list[e]:
                    messages.append('{} is too short'.format(e.upper()))
                elif 'max length is' in error_list[e]:
                    messages.append('{} is too long'.format(e.upper()))
                else:
                    messages.append('{} {}'.format(e.upper(), error_list[e]))

                for message in messages:
                    if use_headline:
                        headline = '{}: {}'.format(doc['validate'].get('headline',
                                                                       doc['validate'].get('_id')), message)
                        response.append(headline)
                    else:
                        response.append(message)
            return response
        else:
            logger.warn('validator was not found for {}'.format(doc['act']))
            return []

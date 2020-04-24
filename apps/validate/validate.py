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
from _collections_abc import MutableMapping
from superdesk.signals import item_validate


REQUIRED_FIELD = 'is a required field'
MAX_LENGTH = 'max length is {length}'
STRING_FIELD = 'require a string value'
DATE_FIELD = 'require a date value'
REQUIRED_ERROR = '{} is a required field'
INVALID_CHAR = 'contains invalid characters'


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

    def _validate_type_related_content(self, field, value):
        """Allow type related_content in schema."""
        pass

    def _validate_type_embed(self, field, value):
        """Allow type media in schema."""
        pass

    def _validate_type_custom(self, field, value):
        """Allow custom field type."""
        pass

    def _validate_type_date(self, field, value):
        if not isinstance(value, datetime):
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

    def _validate_type_any(self, field, value):
        """Allow type any, ex: for CV of type 'custom'."""
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
        if field == "subject":
            # for subject, we have to ignore all data with scheme
            # as they are used for custom values except "subject_custom" scheme as it's the scheme for subject cv
            # so it must be present
            subject_schemas = set([
                None,
                '',
                'subject_custom',
            ])

            # plus any cv with schema_field subject
            cvs = get_resource_service('vocabularies').get_from_mongo(
                req=None, lookup={'schema_field': field}, projection={'_id': 1})
            for cv in cvs:
                subject_schemas.add(cv['_id'])

            filtered = [v for v in value if v.get('scheme') in subject_schemas]

            if not filtered:
                self._error(field, REQUIRED_FIELD)

        elif isinstance(value, list) and not value:
            self._error(field, REQUIRED_FIELD)
        elif isinstance(value, str) and value == '<p></p>':  # default value for editor3
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

    def _validate_validate_characters(self, validate, field, value):
        """Validate if field contains only allowed characters."""
        disallowed_characters = app.config.get('DISALLOWED_CHARACTERS')

        if validate and disallowed_characters and value:
            invalid_chars = [char for char in disallowed_characters if char in value]
            if invalid_chars:
                return self._error(field, INVALID_CHAR)

    def _validate_media_metadata(self, validate, associations_field, associations):
        if not validate:
            return
        media_metadata_schema = app.config.get('VALIDATOR_MEDIA_METADATA')
        if not media_metadata_schema:
            return
        for assoc_name, assoc_data in associations.items():
            if assoc_data is None or assoc_data.get('type') == 'text':
                continue
            for field, schema in media_metadata_schema.items():
                if schema.get('required', False) and not assoc_data.get(field):
                    self._error("media's " + field, REQUIRED_FIELD)
                try:
                    max_length = int(schema['maxlength'])
                except KeyError:
                    pass
                except ValueError:
                    logger.error('Invalid max length value for media field {field}'.format(field=field))
                else:
                    if assoc_data.get(field) is not None and len(assoc_data[field]) > max_length:
                        self._error("media's " + field, MAX_LENGTH.format(length=max_length))


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

    def create(self, docs, fields=False, **kwargs):
        for doc in docs:
            test_doc = deepcopy(doc)
            doc['errors'] = self._validate(test_doc, fields=fields, **kwargs)
        return [doc['errors'] for doc in docs]

    def _get_profile_schema(self, schema, doc):
        doc['validate'].setdefault('extra', {})  # make sure extra is there so it will validate its fields
        extra_field_types = {'text': 'string', 'embed': 'dict', 'date': 'date',
                             'urls': 'list', 'custom': 'any'}
        extra_fields = superdesk.get_resource_service('vocabularies').get_extra_fields()
        schema['extra'] = {'type': 'dict', 'schema': {}}
        for extra_field in extra_fields:
            if schema.get(extra_field['_id']) and \
                    extra_field.get('field_type', None) in extra_field_types:
                rules = schema.pop(extra_field['_id'])
                rules['type'] = extra_field_types.get(extra_field['field_type'], 'string')
                schema['extra']['schema'].update({extra_field['_id']: get_validator_schema(rules)})
                self._populate_extra(doc['validate'], extra_field['_id'])
        try:
            # avoid errors when cv is removed and value is still there
            schema['subject']['schema']['schema']['scheme'].pop('allowed', None)
        except KeyError:
            pass
        return [{'schema': schema}]

    def _get_validators(self, doc):
        """Get validators.

        In case there is profile defined for item with respective content type it will
        use its schema for validations, otherwise it will fall back to action/item_type filter.
        """
        profile = doc['validate'].get('profile')
        if profile and (app.config['AUTO_PUBLISH_CONTENT_PROFILE'] or doc['act'] != 'auto_publish'):
            content_type = superdesk.get_resource_service('content_types').find_one(req=None, _id=profile)
            if content_type:
                return self._get_profile_schema(content_type.get('schema', {}), doc)
        lookup = {'act': doc['act'], 'type': doc[ITEM_TYPE]}
        if doc.get('embedded'):
            lookup['embedded'] = doc['embedded']
        else:
            lookup['$or'] = [{'embedded': {'$exists': False}}, {'embedded': False}]
        custom_schema = app.config.get('SCHEMA', {}).get(doc[ITEM_TYPE])
        if custom_schema:  # handle custom schema like profile schema
            return self._get_profile_schema(custom_schema, doc)
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

    def _get_media_fields(self, field_schema, field_associations, doc,):
        """Returns the field names in associations. For multiple valued media fields
        the field asssociations name is different from the field schema name.
        :param field_schema: Field schema name
        :param field_associations: Field associations name
        :param doc: Article to be validated
        """

        fields = []
        if field_associations in doc.get('associations', {}):
            return [field_associations]
        media_multivalue_field = field_schema + '--'
        for media_field in doc.get('associations', {}):
            if media_field.startswith(media_multivalue_field) and \
                    doc.get('associations', {}).get(media_field):
                fields.append(media_field)
        return fields

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
            media_fields = self._get_media_fields(field_schema, field_associations, doc)
            for media_field in media_fields:
                if media_field and isinstance(doc['associations'][media_field], MutableMapping):
                    doc[field_schema] = doc['associations'][media_field]
                    if media_field != 'featuremedia':
                        del doc['associations'][media_field]
                    elif not doc.get('feature_media', None) is None and 'description_text' in doc['feature_media']:
                        doc['media_description'] = doc['feature_media']['description_text']

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

    def _process_media_metadata(self, doc, schema):
        """Request media validation if associations is present

        :param doc:
        :param schema:
        :return:
        """
        if doc.get('associations'):
            schema.setdefault('associations', {})['media_metadata'] = True

    def _get_validator_schema(self, validator):
        """Get schema for given validator.

        And make sure there is no `None` value which would raise an exception.
        """
        return {field: get_validator_schema(schema) for field, schema in validator['schema'].items() if schema}

    def _get_vocabulary_display_name(self, vocabulary_id):
        if vocabulary_id == 'anpa_category':
            vocabulary = get_resource_service('vocabularies').find_one(req=None, _id='categories')
        else:
            vocabulary = get_resource_service('vocabularies').find_one(req=None, _id=vocabulary_id)
        if vocabulary and 'display_name' in vocabulary:
            return vocabulary['display_name']
        return vocabulary_id

    def _set_default_subject_scheme(self, item):
        if item.get('subject'):
            for subject in item['subject']:
                subject.setdefault('scheme', None)

    def _validate(self, doc, fields=False, **kwargs):
        item = deepcopy(doc['validate'])  # make a copy for signal before validation processing
        use_headline = kwargs and 'headline' in kwargs
        validators = self._get_validators(doc)
        for validator in validators:
            validation_schema = self._get_validator_schema(validator)
            self._sanitize_fields(doc['validate'], validator)
            self._set_default_subject_scheme(doc['validate'])
            self._process_media(doc['validate'], validation_schema)
            self._process_sms(doc['validate'], validation_schema)
            self._process_media_metadata(doc['validate'], validation_schema)
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
                elif 'required field' in error_list[e] or type(error_list[e]) is dict or type(error_list[e]) is list:
                    display_name = self._get_vocabulary_display_name(e)
                    messages.append(REQUIRED_ERROR.format(display_name.upper()))
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

            # let custom code do additional validation
            item_validate.send(self, item=item, response=response, error_fields=v.errors)

            if fields:
                return response, v.errors
            return response
        else:
            logger.warn('validator was not found for {}'.format(doc['act']))
            if fields:
                return [], {}
            return []

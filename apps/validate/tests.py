# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.validate.validate import SchemaValidator, ValidateService
from superdesk.tests import TestCase


class ValidateMandatoryInListTest(TestCase):

    def test_fail_validate_mandatory_in_list_for_subject(self):
        validator = SchemaValidator()
        mandatory = {'scheme': {'subject': 'custom_subject', 'category': 'category'}}
        field = 'scheme'
        value = [{'name': 'DiDFødselsdag', 'qcode': 'DiDFødselsdag',
                  'scheme': 'category', 'service': {'d': 1, 'i': 1}}]
        validator._validate_mandatory_in_list(mandatory, field, value)

        self.assertEqual(validator._errors['subject'], 'is a required field')

    def test_fail_validate_mandatory_in_list_for_subject_and_category(self):
        validator = SchemaValidator()
        mandatory = {'scheme': {'subject': 'custom_subject', 'category': 'category'}}
        field = 'scheme'
        value = []
        validator._validate_mandatory_in_list(mandatory, field, value)

        self.assertEqual(validator._errors['subject'], 'is a required field')
        self.assertEqual(validator._errors['category'], 'is a required field')

    def test_validate_mandatory_in_list(self):
        validator = SchemaValidator()
        mandatory = {'scheme': {'subject': 'subject_custom', 'category': 'category'}}
        field = 'scheme'
        value = [{'name': 'DiDFødselsdag', 'qcode': 'DiDFødselsdag',
                  'scheme': 'category', 'service': {'d': 1, 'i': 1}},
                 {'name': 'arkeologi', 'qcode': '01001000', 'scheme': 'subject_custom', 'parent': '01000000'}]
        validator._validate_mandatory_in_list(mandatory, field, value)

        self.assertEqual(validator._errors, {})

    def test_sanitize_fields_not_in_schema(self):
        doc = {'body_html': 'test'}
        service = ValidateService()
        schema = {'schema': {'body_html': None}}
        service._sanitize_fields(doc, schema)
        self.assertEqual('test', doc['body_html'])

    def test_validate_field_without_schema(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'headline': {'required': True},
        }}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {'profile': 'foo', 'slugline': 'foo'},
            },
        ])
        self.assertEqual(['HEADLINE is a required field'], errors[0])

    def test_validate_required_empty_string(self):
        self.app.data.insert('content_types', [
            {'_id': 'foo', 'schema': {'headline': {'required': True}}}
        ])

        service = ValidateService()
        errors = service.create([
            {'act': 'test', 'type': 'test', 'validate': {'profile': 'foo', 'headline': ''}}
        ])

        self.assertEqual(['HEADLINE empty values not allowed'], errors[0])

    def test_validate_required_empty_list(self):
        self.app.data.insert('content_types', [
            {'_id': 'foo', 'schema': {'subject': {'type': 'list', 'required': True}}}
        ])

        service = ValidateService()
        errors = service.create([
            {'act': 'test', 'type': 'test', 'validate': {'profile': 'foo', 'subject': []}}
        ])

        self.assertEqual(errors, [['SUBJECT is a required field']])

    def test_validate_required_none_list(self):
        self.app.data.insert('content_types', [{
            '_id': 'foo',
            'schema': {
                'subject': {
                    'type': 'list',
                    'required': True,
                    'mandatory_in_list': {'scheme': {'subject': 'subject_custom', 'category': 'category'}},
                    'schema': {
                        'type': 'dict',
                        'schema': {
                            'name': {},
                            'qcode': {},
                            'scheme': {
                                'type': 'string',
                                'required': True,
                                'allowed': ['subject_custom', 'category']
                            },
                            'service': {'nullable': True},
                            'parent': {'nullable': True}
                        }
                    }
                }
            }
        }])

        service = ValidateService()
        errors = service.create([
            {'act': 'test', 'type': 'test', 'validate': {'profile': 'foo', 'subject': None}}
        ])

        self.assertEqual(errors, [['SUBJECT is a required field']])

    def test_validate_field_required_feature_media(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'feature_media': {'required': True},
        }}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {'profile': 'foo', 'slugline': 'foo'},
            },
        ])
        self.assertEqual(['FEATURE_MEDIA is a required field'], errors[0])

    def test_validate_field_required_media_description(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'feature_media': {'required': True},
            'media_description': {'required': True},
        }}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {'profile': 'foo', 'slugline': 'foo', 'associations': {'featuremedia': {}}},
            },
        ])
        self.assertEqual(['MEDIA_DESCRIPTION is a required field'], errors[0])

    def test_validate_field_feature_media_and_media_description(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'feature_media': {'required': True},
            'media_description': {'required': True},
        }}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {
                    'profile': 'foo',
                    'slugline': 'foo',
                    'associations': {'featuremedia': {'description_text': 'test'}}
                },
            },
        ])
        self.assertEqual(errors, [[]])

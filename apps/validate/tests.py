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
from superdesk.metadata.item import ITEM_TYPE


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

    def test_validate_date_with_success(self):
        validator = SchemaValidator()
        validator._validate_type_date('test1', '2017-11-22T22:11:33+0000')
        self.assertEqual(validator._errors, {})

    def test_validate_date_with_error(self):
        validator = SchemaValidator()
        validator._validate_type_date('test1', '2017-11-33T22:11:33+0000')
        self.assertEqual(validator._errors, {'test1': 'require a date value'})

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

    def test_validate_field_required_media_description_empty(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'feature_media': {'required': True, 'type': 'media'},
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

    def test_validate_field_required_media_description_null(self):
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
                'validate': {'profile': 'foo', 'slugline': 'foo', 'associations': {'featuremedia': None}},
            },
        ])
        self.assertIn('FEATURE_MEDIA is a required field', errors[0])
        self.assertIn('MEDIA_DESCRIPTION is a required field', errors[0])

    def test_validate_field_required_media_description_required_false(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'feature_media': {'required': False, 'type': 'media'},
            'media_description': {'required': False},
        }}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {'profile': 'foo', 'slugline': 'foo', 'associations': {'featuremedia': None}},
            },
        ])

        self.assertIn('FEATURE_MEDIA is a required field', errors[0])

    def test_validate_field_required_media_description_required_false_null_true(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'feature_media': {'required': False, 'nullable': True, 'type': 'media'},
            'media_description': {'required': False, 'nullable': True},
        }}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {'profile': 'foo', 'slugline': 'foo', 'associations': {'featuremedia': None}},
            },
        ])

        self.assertEqual([], errors[0])

    def test_validate_field_feature_media_and_media_description(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'slugline': None,
            'feature_media': {'required': True, 'type': 'media'},
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

    def test_validate_custom_fields(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'embed1': {
                "required": True,
                "enabled": True,
                "type": "embed",
                "nullable": False
            },
            'text1': {
                "minlength": 10,
                "required": True,
                "enabled": True,
                "type": "text",
                "maxlength": 160,
                "nullable": False
            },
            'date1': {
                "required": True,
                "enabled": True,
                "type": "date",
                "nullable": False
            }
        }}])
        self.app.data.insert('vocabularies', [
            {'_id': 'embed1', 'type': 'manageable', 'field_type': 'embed'},
            {'_id': 'text1', 'type': 'manageable', 'field_type': 'text'},
            {'_id': 'date1', 'type': 'manageable', 'field_type': 'date'}
        ])
        service = ValidateService()
        doc = {
            'act': 'test',
            ITEM_TYPE: 'test',
            'validate': {
                'profile': 'foo'
            }
        }
        schema = {'extra': {
            'schema': {
                'embed1': {
                    'required': True,
                    'enabled': True,
                    'nullable': False,
                    'empty': False,
                    'type': 'dict'
                },
                'text1': {
                    'enabled': True,
                    'required': True,
                    'nullable': False,
                    'minlength': 10,
                    'maxlength': 160,
                    'type': 'string'
                },
                'date1': {
                    'required': True,
                    'enabled': True,
                    'nullable': False,
                    'empty': False,
                    'type': 'date'
                },
            },
            'type': 'dict'
        }}
        self.assertEqual(service._get_validators(doc)[0]['schema'], schema)

    def test_sanitize_text_fields(self):
        item = {
            'headline': '<p>headline</p>',
            'extra': {'text1': '<p>text 1</p>'}
        }
        sanitized_item = {
            'headline': 'headline',
            'extra': {'text1': 'text 1'}
        }
        validator = {
            'schema': {
                'headline': {
                    'maxlength': 64, 'nullable': True, 'required': False, 'type': 'string'
                },
                'extra': {
                    'schema': {
                        'text1': {
                            'maxlength': 10, 'nullable': True, 'required': False, 'type': 'string'
                        }
                    }
                }
            }
        }
        ValidateService()._sanitize_fields(item, validator)
        self.assertEqual(item, sanitized_item)

    def test_validate_field_sms(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'sms': {
                "minlength": 10,
                "required": True,
                "enabled": True,
                "type": "string",
                "maxlength": 160,
                "nullable": True
            }}}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {'profile': 'foo',
                             'flags': {'marked_for_sms': True},
                             'sms_message': 'short'
                             },
            },
        ])
        self.assertEqual(['SMS is too short'], errors[0])

    def test_validate_field_sms_not_enabled(self):
        self.app.data.insert('content_types', [{'_id': 'foo', 'schema': {
            'sms': {
                "minlength": 10,
                "required": True,
                "enabled": True,
                "type": "string",
                "maxlength": 160,
                "nullable": True
            }}}])
        service = ValidateService()
        errors = service.create([
            {
                'act': 'test',
                'type': 'test',
                'validate': {'profile': 'foo',
                             'flags': {'marked_for_sms': False},
                             'sms_message': 'short'
                             },
            },
        ])
        self.assertEqual(errors, [[]])

    def test_validate_process_media(self):
        item = {
            'associations': {
                'media1--1': {
                    'headline': 'media 1'
                }
            }
        }
        validation_schema = {
            'media1': {'required': True}
        }
        ValidateService()._process_media(item, validation_schema)
        self.assertIn('media1', item)
        self.assertEqual(item['associations']['media1--1'], item['media1'])

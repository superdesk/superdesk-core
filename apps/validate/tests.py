# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from test_factory import SuperdeskTestCase
from apps.validate.validate import SchemaValidator


class ValidateMandatoryInListTest(SuperdeskTestCase):

    def test_fail_validate_mandatory_in_list_for_subject(self):
        validator = SchemaValidator()
        mandatory = {"scheme": {"subject": "custom_subject", "category": "category"}}
        field = "scheme"
        value = [{"name": "DiDFødselsdag", "qcode": "DiDFødselsdag",
                  "scheme": "category", "service": {"d": 1, "i": 1}}]
        validator._validate_mandatory_in_list(mandatory, field, value)

        self.assertEqual(validator._errors['subject'], 'is a required field')

    def test_fail_validate_mandatory_in_list_for_subject_and_category(self):
        validator = SchemaValidator()
        mandatory = {"scheme": {"subject": "custom_subject", "category": "category"}}
        field = "scheme"
        value = []
        validator._validate_mandatory_in_list(mandatory, field, value)

        self.assertEqual(validator._errors['subject'], 'is a required field')
        self.assertEqual(validator._errors['category'], 'is a required field')

    def test_validate_mandatory_in_list(self):
        validator = SchemaValidator()
        mandatory = {"scheme": {"subject": "subject_custom", "category": "category"}}
        field = "scheme"
        value = [{"name": "DiDFødselsdag", "qcode": "DiDFødselsdag",
                  "scheme": "category", "service": {"d": 1, "i": 1}},
                 {"name": "arkeologi", "qcode": "01001000", "scheme": "subject_custom", "parent": "01000000"}]
        validator._validate_mandatory_in_list(mandatory, field, value)

        self.assertEqual(validator._errors, {})

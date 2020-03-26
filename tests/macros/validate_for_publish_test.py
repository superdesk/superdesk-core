# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from nose.tools import assert_raises

from superdesk.tests import TestCase
from superdesk.macros.validate_for_publish import validate_for_publish, ValidationError


class ValidateForPublishTests(TestCase):
    validator = {'_id': 'publish_text',
                 'act': 'publish',
                 'type': 'text',
                 'schema': {
                     'headline': {
                         'required': True,
                         'maxlength': 5,
                         'empty': False,
                         'nullable': False,
                         'type': "string"
                     }
                 }
                 }

    def test_validator(self):
        self.app.data.insert('archive', [{'_id': 1, 'type': 'text', 'headline': '123456'}])
        self.app.data.insert('validators', [self.validator])
        with self.app.app_context():
            with assert_raises(ValidationError):
                item = {'_id': 1}
                validate_for_publish(item)

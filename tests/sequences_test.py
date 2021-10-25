# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk import get_resource_service
from superdesk.tests import TestCase
from nose.tools import assert_raises


class SequencesTestCase(TestCase):
    def setUp(self):
        with self.app.app_context():
            self.service = get_resource_service("sequences")
        self.min_seq_number = 1
        self.max_seq_number = 10

    def test_empty_sequence_name_fails(self):
        with self.app.app_context():
            with assert_raises(KeyError):
                self.service.get_next_sequence_number(None)
                self.service.get_next_sequence_number("")

    def test_next_sequence_number(self):
        with self.app.app_context():
            sequence_number1 = self.service.get_next_sequence_number("test_sequence_1")
            sequence_number2 = self.service.get_next_sequence_number("test_sequence_1")
            self.assertEqual(sequence_number1 + 1, sequence_number2)

    def test_rotate_sequence_number(self):
        with self.app.app_context():

            last_sequence_number = None
            for i in range(self.max_seq_number):
                last_sequence_number = self.service.get_next_sequence_number(
                    "test_sequence_1", max_seq_number=self.max_seq_number, min_seq_number=self.min_seq_number
                )
            self.assertEqual(last_sequence_number, self.max_seq_number)

            for i in range(0, 2):
                last_sequence_number = self.service.get_next_sequence_number(
                    "test_sequence_1", max_seq_number=self.max_seq_number, min_seq_number=self.min_seq_number
                )
                self.assertEqual(last_sequence_number, self.min_seq_number + i, "failed for i={}".format(i))

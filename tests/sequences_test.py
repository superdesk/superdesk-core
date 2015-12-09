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


class SequencesTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.resource_name = 'subscribers'
        with self.app.app_context():
            self.subscribers_service = get_resource_service(self.resource_name)
            self.sequences_service = get_resource_service('sequences')
        self.min_seq_number = 0
        self.max_seq_number = 10

    def test_next_sequence_number_for_item(self):
        with self.app.app_context():
            subscriber_id = self.subscribers_service.create({})
            sequence_number1 = self.sequences_service.get_next_sequence_number_for_item(
                resource_name=self.resource_name,
                query_value=subscriber_id,
                max_seq_number=self.max_seq_number,
                min_seq_number=self.min_seq_number
            )
            sequence_number2 = self.sequences_service.get_next_sequence_number_for_item(
                resource_name=self.resource_name,
                query_value=subscriber_id,
                max_seq_number=self.max_seq_number,
                min_seq_number=self.min_seq_number
            )
            self.assertEqual(sequence_number1 + 1, sequence_number2)

    def test_rotate_sequence_number(self):
        with self.app.app_context():
            subscriber_id = self.subscribers_service.create({})

            for i in range(self.max_seq_number + 1):
                last_sequence_number = self.sequences_service.get_next_sequence_number_for_item(
                    resource_name=self.resource_name,
                    query_value=subscriber_id,
                    max_seq_number=self.max_seq_number,
                    min_seq_number=self.min_seq_number
                )
            self.assertEqual(last_sequence_number, self.max_seq_number)

            last_sequence_number = self.sequences_service.get_next_sequence_number_for_item(
                resource_name=self.resource_name,
                query_value=subscriber_id,
                max_seq_number=self.max_seq_number,
                min_seq_number=self.min_seq_number
            )
            self.assertEqual(last_sequence_number, self.min_seq_number)

    def test_next_sequence_number_for_key(self):
        with self.app.app_context():
            sequence_number1 = self.sequences_service.get_next_sequence_number_for_key(
                'test_sequence_1'
            )
            sequence_number2 = self.sequences_service.get_next_sequence_number_for_key(
                'test_sequence_1'
            )
            self.assertEqual(sequence_number1 + 1, sequence_number2)

    def test_rotate_sequence_number_for_key(self):
        with self.app.app_context():

            for i in range(self.max_seq_number + 1):
                last_sequence_number = self.sequences_service.get_next_sequence_number_for_key(
                    'test_sequence_1',
                    max_seq_number=self.max_seq_number,
                    min_seq_number=self.min_seq_number
                )
            self.assertEqual(last_sequence_number, self.max_seq_number)

            last_sequence_number = self.sequences_service.get_next_sequence_number_for_key(
                'test_sequence_1',
                max_seq_number=self.max_seq_number,
                min_seq_number=self.min_seq_number
            )
            self.assertEqual(last_sequence_number, self.min_seq_number)

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
from superdesk.tests import TestCase
from superdesk.publish.subscribers import SubscribersService
from superdesk.sequences import get_next_sequence_number


class SequencesTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.resource_name = 'subscribers'
        with self.app.app_context():
            self.service = SubscribersService(self.resource_name, backend=superdesk.get_backend())
        self.min_seq_number = 0
        self.max_seq_number = 10

    def test_next_sequence_number(self):
        with self.app.app_context():
            subscriber_id = self.service.create({})
            sequence_number1 = get_next_sequence_number(
                resource_name=self.resource_name,
                item_id=subscriber_id,
                max_seq_number=self.max_seq_number,
                min_seq_number=self.min_seq_number
            )
            sequence_number2 = get_next_sequence_number(
                resource_name=self.resource_name,
                item_id=subscriber_id,
                max_seq_number=self.max_seq_number,
                min_seq_number=self.min_seq_number
            )
            self.assertEqual(sequence_number1 + 1, sequence_number2)

    def test_rotate_sequence_number(self):
        with self.app.app_context():
            subscriber_id = self.service.create({})

            for i in range(self.max_seq_number + 1):
                last_sequence_number = get_next_sequence_number(
                    resource_name=self.resource_name,
                    item_id=subscriber_id,
                    max_seq_number=self.max_seq_number,
                    min_seq_number=self.min_seq_number
                )
            self.assertEqual(last_sequence_number, self.max_seq_number)

            last_sequence_number = get_next_sequence_number(
                resource_name=self.resource_name,
                item_id=subscriber_id,
                max_seq_number=self.max_seq_number,
                min_seq_number=self.min_seq_number
            )
            self.assertEqual(last_sequence_number, self.min_seq_number)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
from superdesk.tests import TestCase

from superdesk.io.feed_parsers.ap_anpa import AP_ANPAFeedParser


def fixture(filename):
    dirname = os.path.dirname(os.path.realpath(__file__))
    return os.path.normpath(os.path.join(dirname, '../fixtures', filename))


class ANPATestCase(TestCase):

    parser = AP_ANPAFeedParser()

    def setUp(self):
        with self.app.app_context():
            vocab = [{'_id': 'categories', 'items': [{'is_active': True, 'name': 'Domestic Sport', 'qcode': 's'}]}]
            self.app.data.insert('vocabularies', vocab)

    def open(self, filename):
        provider = {'name': 'Test'}
        return self.parser.parse(fixture(filename), provider)

    def test_ed_note(self):
        item = self.open('anpa-2.tst')
        self.assertEqual('This is part of an Associated Press investigation into the hidden costs of green energy.',
                         item['ednote'])
        self.assertEqual('1stLd-Writethru', item['anpa_take_key'])
        self.assertEqual('i', item['anpa_category'][0]['qcode'])

    def test_subject_expansion(self):
        item = self.open('ap_anpa-1.tst')
        self.assertEqual(item['subject'][0]['qcode'], '15008000')
        self.assertEqual(item['dateline']['text'], 'ATLANTA, Feb 19 AP -')

    def test_table_story(self):
        item = self.open('ap_anpa-2.tst')
        self.assertEqual(item['slugline'], 'BBO--BaseballExpanded')
        self.assertEqual(item['format'], 'preserved')
        self.assertGreater(item['body_html'].find('%08Baltimore;23;13;.639;_;_;8-2;L-1;16-6;7-7'), 0)

    def test_unknown_category_defaults_to_i(self):
        item = self.open('ap_anpa-3.tst')
        self.assertEqual(item['anpa_category'][0]['qcode'], 'i')

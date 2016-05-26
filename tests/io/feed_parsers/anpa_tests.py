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

from superdesk.io.feed_parsers.anpa import ANPAFeedParser


def fixture(filename):
    dirname = os.path.dirname(os.path.realpath(__file__))
    return os.path.normpath(os.path.join(dirname, '../fixtures', filename))


class ANPATestCase(TestCase):

    parser = ANPAFeedParser()

    def open(self, filename):
        provider = {'name': 'Test'}
        return self.parser.parse(fixture(filename), provider)

    def test_open_anpa_file(self):
        item = self.open('anpa-1.tst')
        self.assertEqual('text', item['type'])
        self.assertEqual('2870', item['provider_sequence'])
        self.assertEqual(1, item['priority'])
        self.assertEqual('l', item['anpa_category'][0]['qcode'])
        self.assertEqual('text', item['type'])
        self.assertEqual(1049, item['word_count'])
        self.assertEqual('For Argentine chemo patients, mirrors can hurt', item['headline'])
        self.assertEqual('By PAUL BYRNE and ALMUDENA CALATRAVA', item['byline'])
        self.assertRegex(item['body_html'], '^<p>BUENOS')
        self.assertEqual('Argentina-Cancer', item['slugline'])
        self.assertEqual('2013-11-13T15:09:00+00:00', item['firstcreated'].isoformat())

    def test_ed_note(self):
        item = self.open('anpa-2.tst')
        self.assertEqual('This is part of an Associated Press investigation into the hidden costs of green energy.',
                         item['ednote'])
        self.assertEqual('1stLd-Writethru', item['anpa_take_key'])

    def test_tab_content(self):
        item = self.open('anpa-3.tst')
        self.assertEqual('preserved', item['format'])

    def test_header_lines_only(self):
        item = self.open('anpa-4.tst')
        self.assertEqual('text', item['type'])
        self.assertEqual('HTML', item['format'])
        self.assertRegex(item['body_html'], '<p>Ex-bodyguard testifies about lewd messages sent to Paltrow')

    def test_map_priority(self):
        self.assertEqual(1, self.parser.map_priority('F'))
        self.assertEqual(2, self.parser.map_priority('U'))
        self.assertEqual(1, self.parser.map_priority('f'))
        self.assertEqual(3, self.parser.map_priority('b'))
        self.assertEqual(6, self.parser.map_priority('z'))
        self.assertEqual(6, self.parser.map_priority(None))
        self.assertEqual(6, self.parser.map_priority('dd'))

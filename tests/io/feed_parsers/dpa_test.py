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

from superdesk.io.feed_parsers.dpa_iptc7901 import DPAIPTC7901FeedParser
from superdesk.tests import TestCase


def fixture(filename):
    dirname = os.path.dirname(os.path.realpath(__file__))
    return os.path.normpath(os.path.join(dirname, '../fixtures', filename))


class DPAIptcTestCase(TestCase):

    parser = DPAIPTC7901FeedParser()

    def open(self, filename):
        provider = {'name': 'Test'}
        return self.parser.parse(fixture(filename), provider)

    def test_open_iptc7901_file(self):
        with self.app.app_context():
            item = self.open('IPTC7901.txt')
            self.assertEqual('text', item['type'])
            self.assertEqual('062', item['ingest_provider_sequence'])
            self.assertEqual('i', item['anpa_category'][0]['qcode'])
            self.assertEqual(211, item['word_count'])
            self.assertEqual('Germany Social Democrats: Coalition talks with Merkel could fail', item['headline'])
            self.assertRegex(item['body_html'], '^<p></p><p>Negotiations')
            self.assertEqual('Germany-politics', item['slugline'])
            self.assertEqual(4, item['priority'])
            self.assertEqual([{'qcode': 'i'}], item['anpa_category'])
            self.assertTrue(item['ednote'].find('## Editorial contacts'))
            self.assertEqual(item['dateline']['source'], 'dpa')
            self.assertEqual(item['dateline']['located']['city'], 'Berlin')

    def test_open_dpa_copyright(self):
        with self.app.app_context():
            item = self.open('dpa_copyright.txt')
            self.assertEqual('text', item['type'])
            self.assertEqual('rs', item['anpa_category'][0]['qcode'])
            self.assertEqual('Impressum', item['headline'])
            self.assertEqual('Impressum', item['slugline'])
            self.assertEqual('(Achtung)', item['anpa_take_key'])

    def test_four_line_header(self):
        with self.app.app_context():
            item = self.open('dpa_four_line.txt')
            self.assertEqual('Switzerland joins list of countries resisting UN migration pact', item['headline'])
            self.assertEqual('Switzerland/migration/UN', item['slugline'])
            self.assertEqual('REFILE 1ST LEAD', item['anpa_take_key'])

    def test_two_line_header(self):
        with self.app.app_context():
            item = self.open('dpa_two_line.txt')
            self.assertEqual('Peace talks on Yemen to take place in Sweden next month, Mattis says', item['headline'])
            self.assertEqual('Yemen/conflict', item['slugline'])
            self.assertEqual('EXTRA', item['anpa_take_key'])

    def test_two_by_line_header(self):
        with self.app.app_context():
            item = self.open('dpa_two_by_line.txt')
            self.assertEqual('Chiefs-Rams 2.0? Would be a fun Super Bowl, but don\'t count on it', item['headline'])
            self.assertEqual('American Football/NFL', item['slugline'])

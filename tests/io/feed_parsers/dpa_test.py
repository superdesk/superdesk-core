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
            self.assertEqual('Germany Social Democrats: Coalition talks with Merkel could fail =', item['headline'])
            self.assertRegex(item['body_html'], '^<p></p><p>Negotiations')
            self.assertEqual('Germany-politics', item['slugline'])
            self.assertEqual(4, item['priority'])
            self.assertEqual([{'qcode': 'i'}], item['anpa_category'])
            self.assertTrue(item['ednote'].find('## Editorial contacts'))
            self.assertEqual(item['dateline']['source'], 'dpa')
            self.assertEqual(item['dateline']['located']['city'], 'Berlin')

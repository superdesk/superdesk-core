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

from superdesk.io.iptc7901 import Iptc7901FileParser


def fixture(filename):
    dirname = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(dirname, 'fixtures', filename)


class IptcTestCase(TestCase):

    parser = Iptc7901FileParser()

    def open(self, filename):
        return self.parser.parse_file(fixture(filename))

    def test_open_iptc7901_file(self):
        with self.app.app_context():
            item = self.open('IPTC7901.txt')
            self.assertEqual('preformatted', item['type'])
            self.assertEqual('062', item['ingest_provider_sequence'])
            self.assertEqual('i', item['anpa_category'][0]['qcode'])
            self.assertEqual(211, item['word_count'])
            self.assertEqual('Germany Social Democrats: Coalition talks with Merkel could fail =', item['headline'])
            self.assertRegex(item['body_html'], '^\n   Berlin')
            self.assertEqual('Germany-politics', item['slugline'])
            self.assertEqual(5, item['priority'])
            self.assertEqual([{'qcode': 'i'}], item['anpa_category'])

    def test_map_priority(self):
        self.assertEqual(1, self.parser.map_priority("1"))
        self.assertEqual(2, self.parser.map_priority("2"))
        self.assertEqual(3, self.parser.map_priority("3"))
        self.assertEqual(5, self.parser.map_priority("5"))
        self.assertEqual(5, self.parser.map_priority("eee"))
        self.assertEqual(5, self.parser.map_priority(None))

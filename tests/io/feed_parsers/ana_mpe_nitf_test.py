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
from superdesk.io.feed_parsers.ana_mpe_newsml import ANANewsMLOneFeedParser
from superdesk.etree import etree


class TestANACase(TestCase):
    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ana1.xml'))
        provider = {'name': 'Test', 'source': 'ANA'}
        with open(fixture, 'rb') as f:
            self.item = ANANewsMLOneFeedParser().parse(etree.fromstring(f.read()), provider)

    def test_headline(self):
        self.assertEqual(self.item['headline'], 'Wage employment balance positive in Jan-March')
        self.assertEqual(self.item['subject'][0], {'qcode': '04008004', 'name': 'economic indicator'})
        self.assertEqual(self.item['dateline']['text'], 'ATHENS, April 4 ANA -')
        self.assertTrue(self.item['body_html'].startswith('<p>Wage employment'))
        self.assertTrue(self.item['body_html'].endswith(' job positions.</p>\n<p> </p>'), )
        self.assertEqual(self.item['word_count'], '115')

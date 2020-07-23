#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from superdesk.tests import TestCase
from superdesk.io.feed_parsers.pa_nitf import PAFeedParser
from lxml import etree


class PANITFFileTestCase(TestCase):

    vocab = [{'_id': 'genre', 'items': [{'name': 'Current'}]}]

    def setUpForChildren(self):
        super().setUpForChildren()
        with self.app.app_context():
            self.app.data.insert('vocabularies', self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture, 'rb') as f:
            xml = etree.parse(f)
            self.item = PAFeedParser().parse(xml.getroot(), provider)


class PAFileWithNoSubjects(PANITFFileTestCase):

    filename = 'pa2.xml'

    def test_headline(self):
        self.assertEqual(self.item.get('headline'), 'Soccer INT-Teams')

    def test_anpa_category(self):
        self.assertEqual(self.item.get('anpa_category'), [{'qcode': 'S'}])


class PATestCase(PANITFFileTestCase):

    filename = 'pa1.xml'

    def test_slugline(self):
        self.assertEqual(self.item.get('slugline'), 'Sport Trivia (Oct 14)')
        self.assertEqual(self.item.get('headline'), 'PA SPORT TRIVIA (OCTOBER 14)')
        self.assertEqual('usable', self.item.get('pubstatus'))
        self.assertEqual('af1f7ad5-5619-49de-84cc-2e608538c77fSSS-3-1', self.item.get('guid'))
        self.assertEqual(self.item.get('format'), 'HTML')
        self.assertEqual(4, len(self.item.get('subject')))
        self.assertIn('Trivia (Oct 14)', self.item.get('keywords'))
        self.assertIsInstance(self.item.get('word_count'), int)


class PAEmbargoTestCase(PANITFFileTestCase):

    filename = 'pa3.xml'

    def test_slugline(self):
        self.assertEqual(self.item.get('pubstatus'), 'usable')


class PAEntertainmentTest(PANITFFileTestCase):

    filename = 'pa4.xml'

    def test_entertainment_category(self):
        self.assertEqual(self.item.get('anpa_category'), [{'qcode': 'E'}])


class PACharsetConversionTest(PANITFFileTestCase):

    filename = 'pa5.xml'

    def test_charset(self):
        self.assertTrue(self.item['body_html'].startswith('<p>Treasury coffers will take a £66 billion annual hit '
                                                          'if Britain goes for a so-called hard Brexit'))
        self.assertEqual(self.item['headline'], 'HARD BREXIT TO COST UK UP TO £66BN A YEAR, SAYS TREASURY')

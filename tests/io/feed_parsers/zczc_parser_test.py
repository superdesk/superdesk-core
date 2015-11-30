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
import unittest

from superdesk.io.feed_parsers.zczc import ZCZCFeedParser


class ZCZCTestCase(unittest.TestCase):
    provider = {'name': 'test provder', 'provider': {}}

    def test_default_format(self):
        filename = 'Standings__2014_14_635535729050675896.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'SOMETHING'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), 'MOTOR:  Collated results/standings after Sydney NRMA 500')
        self.assertEqual(self.items.get('anpa_category')[0]['qcode'], 'T')
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15039001')
        self.assertIn('versioncreated', self.items)

    def test_medianet_format(self):
        filename = 'ED_841066_2_1.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'MNET'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), 'Australian Financial Security Authority')

    def test_pagemasters_format(self):
        filename = 'Darwin GR - Greys - Sun 11 Oct, 2015.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'PMF'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), 'Darwin Greyhound Fields Sunday')
        self.assertEqual(self.items.get('slugline'), 'Darwin Grey')
        self.assertEqual(self.items.get('anpa_category')[0]['qcode'], 'r')
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15082002')

    def test_racing_format(self):
        filename = 'viflda004_7257.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'BRA'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), ' Racing.Com Park FIELDS Thursday')
        self.assertEqual(self.items.get('anpa_category')[0]['qcode'], 'r')
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15030001')

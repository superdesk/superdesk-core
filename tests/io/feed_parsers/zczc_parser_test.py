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
from test_factory import SuperdeskTestCase
from superdesk.io.feed_parsers.zczc import ZCZCFeedParser


class ZCZCTestCase(SuperdeskTestCase):
    provider = {'name': 'test provder', 'provider': {}}

    validators = [
        {
            'schema': {
                'headline': {
                    'required': True,
                    'maxlength': 64,
                    'empty': False,
                    'nullable': False,
                    'type': "string"
                },
                'slugline': {
                    'required': True,
                    'maxlength': 24,
                    'empty': False,
                    'nullable': False,
                    'type': "string"
                }

            },
            'type': 'text',
            'act': 'publish',
            '_id': 'publish_text'
        }
    ]

    def setUp(self):
        super().setUp()
        self.app.data.insert('validators', self.validators)

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
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15082000')

    def test_racing_format(self):
        filename = 'viflda004_7257.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'BRA'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), ' Racing.Com Park FIELDS Thursday')
        self.assertEqual(self.items.get('slugline'), ' Racing.Com Park FIELDS ')
        self.assertEqual(self.items.get('anpa_category')[0]['qcode'], 'r')
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15030001')

    def test_trot_tab_divs(self):
        filename = 'Wagga Trot VIC TAB DIVS 1-4 Friday.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'PMF'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), 'VIC TAB DIVS 1-4 Friday')
        self.assertEqual(self.items.get('slugline'), 'Wagga Trot')
        self.assertEqual(self.items.get('anpa_category')[0]['qcode'], 'r')
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15030003')

    def test_leading_jockeys(self):
        filename = 'vinlpt_8390.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'BRA'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), 'Leading jockeys (Sydney)')
        self.assertEqual(self.items.get('slugline'), 'Leading jockeys (Sydney)')
        self.assertEqual(self.items.get('anpa_category')[0]['qcode'], 'r')
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15030001')

    def test_weights(self):
        filename = 'viwhtn01_8594.tst'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        self.provider['source'] = 'BRA'
        self.items = ZCZCFeedParser().parse(fixture, self.provider)
        self.assertEqual(self.items.get('headline'), 'STRADBROKE HANDICAP 1400M .=!')
        self.assertEqual(self.items.get('slugline'), 'STRADBROKE HANDICAP 1400')
        self.assertEqual(self.items.get('anpa_category')[0]['qcode'], 'r')
        self.assertEqual(self.items.get('subject')[0]['qcode'], '15030001')

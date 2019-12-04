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
from superdesk.io.feed_parsers.ninjs import NINJSFeedParser


class NINJSTestCase(TestCase):
    vocab = [{'_id': 'genre', 'items': [{'name': 'Current'}]}]

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert('vocabularies', self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        self.items = NINJSFeedParser().parse(fixture, provider)


class SimpleTestCase(NINJSTestCase):

    filename = 'ninjs1.json'

    def test_headline(self):
        self.assertEqual(self.items[0].get('headline'), "headline")
        self.assertEqual(self.items[0].get('description_text'), "abstract")
        self.assertEqual(1, len(self.items[0].get('authors')), 'authors')
        self.assertEqual(self.items[0]['authors'][0], {
            'name': 'John',
            'role': 'writer',
            'avatar_url': 'http://example.com',
            'biography': 'bio',
        })
        self.assertNotIn("source", self.items[0])
        self.assertEqual(self.items[0]['original_source'], "AAP")
        self.assertEqual('2017-08-24T04:38:34+00:00', self.items[0]['versioncreated'].isoformat())


class AssociatedTestCase(NINJSTestCase):

    filename = 'ninjs2.json'

    def test_parsed_items(self):
        # The picture
        self.assertEqual(self.items[0].get('type'), 'picture')
        self.assertEqual(self.items[0].get('headline'), 'Financial Markets')
        self.assertEqual(self.items[0].get('alt_text'), 'Oil markets something')
        self.assertEqual(self.items[0].get('description_text'),
                         'Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.')
        # The text item
        self.assertEqual(self.items[1].get('type'), 'text')
        self.assertEqual(self.items[1].get('headline'), 'Oil prices edge up on first drop in US drilling in months')
        self.assertEqual(self.items[1].get('abstract'),
                         'Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.')
        # The associated picture in the text item
        self.assertEqual(self.items[1].get('associations').get('featuremedia').get('type'), 'picture')
        self.assertEqual(self.items[1].get('associations').get('featuremedia').get('alt_text'), 'Oil markets something')
        self.assertEqual(self.items[1].get('associations').get('featuremedia').get('description_text'),
                         'Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.')


class PictureTestCase(NINJSTestCase):

    filename = 'ninjs3.json'

    def test_headline(self):
        self.assertEqual(self.items[0].get('headline'), 'German Air Force Museum')
        self.assertEqual(self.items[0].get('type'), "picture")


class IPTCSimpleTextTestCase(NINJSTestCase):
    filename = 'ninjsExSimpleText1.json'

    def test_simple(self):
        self.assertEqual(1, len(self.items))
        item = self.items[0]
        self.assertEqual('urn:ninjs.example.com:newsitems:20130709simp123', item['guid'])
        self.assertEqual('2013-07-09T10:37:00+00:00', item['versioncreated'].isoformat())
        self.assertIn('GROSSETO', item['body_html'])


class IPTCMediumTextTestCase(NINJSTestCase):
    filename = 'ninjsExMediumText1.json'

    def test_medium(self):
        self.assertEqual(1, len(self.items))
        self.assertEqual('text-only', self.items[0]['profile'])
        self.assertEqual('en', self.items[0]['language'])

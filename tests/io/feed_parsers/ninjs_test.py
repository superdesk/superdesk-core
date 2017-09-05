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

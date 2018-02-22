# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.io.feed_parsers.ritzau import RitzauFeedParser
from superdesk.tests import TestCase
from superdesk.etree import etree
import os


class BaseRitzauTestCase(TestCase):

    vocab = [{'_id': 'genre', 'items': [{'name': 'Current'}]}]

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert('vocabularies', self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture, 'rb') as f:
            self.root_elt = etree.fromstring(f.read())
            self.item = RitzauFeedParser().parse(self.root_elt, provider)


class RitzauTestCase(BaseRitzauTestCase):
    filename = 'ritzau_news.xml'

    def test_can_parse(self):
        self.assertTrue(RitzauFeedParser().can_parse(self.root_elt))

    def test_content(self):
        item = self.item
        self.assertEqual(item['version'], 1)
        self.assertEqual(item['byline'], '/ritzau/')
        self.assertEqual(item['body_html'], '<p>Hollandske forskere har "i årevis" lavet forsøg på både '
                                            'mennesker og dyr, hvor de har testet effekten af at indånde '
                                            'udstødningsgas fra dieselbiler.</p><p>Det fortæller forskerne '
                                            'selv til nyhedsbureauet AFP.</p><p>Historien kommer frem på et '
                                            'tidspunkt, hvor tyske bilfabrikanter er udsat for massiv '
                                            'kritik, fordi de har finansieret lignende forsøg.</p>')
        self.assertEqual(item['guid'], '9a6955fc-11da-46b6-9903-439ebb288f2d')
        self.assertEqual(item['firstcreated'].isoformat(), '2018-01-30T17:32:18.397000+01:00')

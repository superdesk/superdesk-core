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

from superdesk.etree import etree
from superdesk.io.feed_parsers.scoop_newsml_2_0 import ScoopNewsMLTwoFeedParser


class ScoopTestCase(unittest.TestCase):
    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture) as f:
            self.scoop = f.read()
            self.item = ScoopNewsMLTwoFeedParser().parse(etree.fromstring(self.scoop), provider)


class AAPTestCase(ScoopTestCase):
    filename = 'scoop.xml'

    def test_content(self):
        self.assertEqual(self.item[0].get('headline'),
                         "Dick Smith receivers install Don Grover as acting CEO as Abboud " +
                         "quits; retailer put up for sale")
        self.assertEqual(self.item[0].get('guid'), 'BD-20160112123540:3')
        self.assertEqual(self.item[0].get('uri'), 'BD-20160112123540')
        self.assertEqual(self.item[0].get('priority'), 5)
        self.assertEqual(self.item[0].get('version'), '3')
        self.assertEqual(self.item[0].get('firstcreated').isoformat(), '2016-01-11T23:35:40+00:00')

    def test_can_parse(self):
        self.assertTrue(ScoopNewsMLTwoFeedParser().can_parse(etree.fromstring(self.scoop)))

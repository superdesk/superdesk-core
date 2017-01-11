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
from superdesk.etree import etree
from superdesk.io.feed_parsers.efe_nitf import EFEFeedParser


class EFENITFTestCase(TestCase):

    filename = 'efe_nitf.xml'

    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture) as f:
            self.nitf = f.read()
            self.item = EFEFeedParser().parse(etree.fromstring(self.nitf), provider)

    def test_item(self):
        self.assertEqual(self.item.get('headline'), "Honduran president announces Cabinet changes")
        self.assertNotIn('byline', self.item)
        self.assertEqual(self.item['dateline']['located']['city'], 'Tegucigalpa')
        self.assertEqual(self.item['subject'][0]['qcode'], '11006005')
        self.assertEqual(self.item['slugline'], 'HONDURAS GOVERNMENT')

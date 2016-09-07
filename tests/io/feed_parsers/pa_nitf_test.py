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
from superdesk.etree import etree


class PANITFFileTestCase(TestCase):

    vocab = [{'_id': 'genre', 'items': [{'name': 'Current'}]}]

    def setUpForChildren(self):
        super().setUpForChildren()
        with self.app.app_context():
            self.app.data.insert('vocabularies', self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture) as f:
            self.nitf = f.read()
            self.item = PAFeedParser().parse(etree.fromstring(self.nitf), provider)


class PAFileWithNoSubjects(PANITFFileTestCase):

    filename = 'pa2.xml'

    def test_headline(self):
        self.assertEqual(self.item.get('headline'), '1 SOCCER INT-Teams')

    def test_anpa_category(self):
        self.assertEqual(self.item.get('anpa_category'), [{'qcode': 'S'}])

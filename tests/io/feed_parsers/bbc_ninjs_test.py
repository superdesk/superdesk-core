# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import hashlib
from superdesk.tests import TestCase
from superdesk.io.feed_parsers.bbc_ninjs import BBCNINJSFeedParser
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, GUID_TAG
from superdesk.metadata.utils import generate_guid


class BBCNINJSTestCase(TestCase):

    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}

        with open(fixture, 'r') as json_file:
            data = json_file.read()

        self.items = BBCNINJSFeedParser().parse(data, provider)


class SimpleTestCase(BBCNINJSTestCase):

    filename = 'bbc-ninjs-text-test.json'

    def test_trans_attributes(self):
        self.assertEqual(self.items[0].get(ITEM_TYPE), CONTENT_TYPE.TEXT)
        self.assertEqual(self.items[0].get('subject')[0].get('qcode'), '11016007')

        guid_hash = hashlib.sha1('https://www.example.com//12345'.encode('utf8')).hexdigest()
        guid = generate_guid(type=GUID_TAG, id=guid_hash)
        self.assertEqual(self.items[0].get('guid'), guid)


class CompositeTestCase(BBCNINJSTestCase):

    filename = 'bbc-ninjs-comp-test.json'

    def test_parsed_items(self):
        # The picture
        self.assertEqual(self.items[1].get(ITEM_TYPE), CONTENT_TYPE.PICTURE)
        self.assertEqual(self.items[1].get('headline'), 'logo-footer.png')
        self.assertEqual(self.items[1].get('description_text'), 'abc')

        # The text item
        self.assertEqual(self.items[0].get(ITEM_TYPE), CONTENT_TYPE.TEXT)
        self.assertEqual(self.items[0].get('headline'), 'abcdef')

        # The associated picture in the text item
        self.assertEqual(self.items[0].get('associations').get('featuremedia').get(ITEM_TYPE), CONTENT_TYPE.PICTURE)
        self.assertEqual(self.items[0].get('associations').get('featuremedia').get('headline'), 'logo-footer.png')
        self.assertEqual(self.items[0].get('associations').get('featuremedia').get('description_text'), 'abc')

        # The composite
        self.assertEqual(self.items[2].get(ITEM_TYPE), CONTENT_TYPE.COMPOSITE)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.io.feed_parsers.image_iptc import ImageIPTCFeedParser
from superdesk.tests import TestCase
import os


class BaseImageIPTCTestCase(TestCase):
    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        self.image_path = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        parser = ImageIPTCFeedParser()
        self.item = parser.parse(self.image_path, provider)


class ImageIPTCTestCase(BaseImageIPTCTestCase):
    filename = 'IPTC-PhotometadataRef-Std2017.1.jpg'

    def test_can_parse(self):
        self.assertTrue(ImageIPTCFeedParser().can_parse(self.image_path))

    def test_content(self):
        item = self.item
        self.assertNotIn('_id', item)
        self.assertEqual(item['headline'], 'The Headline (ref2017.1)')
        self.assertEqual(item['byline'], 'Creator1 (ref2017.1)')
        self.assertEqual(item['slugline'], 'The Title (ref2017.1)')
        self.assertEqual(item['description_text'], 'The description aka caption (ref2017.1)',)
        self.assertEqual(item['keywords'], ['Keyword1ref2017.1', 'Keyword2ref2017.1', 'Keyword3ref2017.1'])
        self.assertEqual(item['ednote'], 'An Instruction (ref2017.1)')
        self.assertEqual(item['copyrightnotice'], 'Copyright (Notice) 2017.1 IPTC - www.iptc.org  (ref2017.1)')
        self.assertEqual(item['assignment_id'], 'Job Id (ref2017.1)')
        self.assertEqual(item['firstcreated'].isoformat(), '2017-07-13T17:01:00+00:00')

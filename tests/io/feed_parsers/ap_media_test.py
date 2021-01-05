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
from superdesk.io.feed_parsers.ap_media import APMediaFeedParser
import json


class APMediaTestCase(TestCase):
    vocab = [{"_id": "genre", "items": [{"name": "Current"}]}]

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert("vocabularies", self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        with open(fixture) as fp:
            self.item = APMediaFeedParser().parse(json.load(fp), provider)


class SimpleTestCase(APMediaTestCase):

    filename = "ap_media_picture.json"

    def test_headline(self):
        self.assertEqual(self.item.get("headline"), "US Paul Simon Poets Society")

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from unittest import mock
import os

from superdesk.tests import TestCase
from superdesk.io.feeding_services import ritzau
from superdesk.io.feed_parsers import ritzau as ritzau_feed

PREFIX = 'test_superdesk_'
PROVIDER = {
    "_id": "test_provider",
    "config": {
        "username": "user",
        "password": "password",
        "feed_parser": "ritzau",
        "field_aliases": []
    },
}


class RitzauTestCase(TestCase):

    def setUp(self):
        super().setUp()
        with self.app.app_context():
            vocab = [{}]
            self.app.data.insert('vocabularies', vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ritzau_feed.xml'))
        with open(fixture) as f:
            self.feed_raw = f.read()

    @mock.patch.object(ritzau, 'requests')
    @mock.patch.object(ritzau.RitzauFeedingService, 'get_feed_parser')
    def test_feeding(self, get_feed_parser, requests):
        get_feed_parser.return_value = ritzau_feed.RitzauFeedParser()
        mock_get = requests.get.return_value
        mock_get.text = self.feed_raw
        provider = PROVIDER.copy()
        service = ritzau.RitzauFeedingService()
        items = service._update(provider, {})[0]
        self.assertEqual(len(items), 2)

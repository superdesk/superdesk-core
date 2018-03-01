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
from superdesk.io.feeding_services import ap
from superdesk.io.feed_parsers import newsml_2_0

PREFIX = 'test_superdesk_'
PROVIDER = {
    "_id": "test_provider",
    "config": {
        "username": "user",
        "password": "password",
        "idList": "123",
        "feed_parser": "newsml2",
        "field_aliases": []
    },
}


class APTestCase(TestCase):

    def setUp(self):
        super().setUp()
        with self.app.app_context():
            vocab = [{}]
            self.app.data.insert('vocabularies', vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ap.xml'))
        with open(fixture, 'rb') as f:
            self.feed_raw = f.read()

    @mock.patch.object(ap, 'requests')
    @mock.patch.object(ap.APFeedingService, 'get_feed_parser')
    def test_feeding(self, get_feed_parser, requests):
        get_feed_parser.return_value = newsml_2_0.NewsMLTwoFeedParser()
        mock_get = requests.get.return_value
        mock_get.content = self.feed_raw
        provider = PROVIDER.copy()
        service = ap.APFeedingService()
        items = service._update(provider, {})[0]
        self.assertEqual(len(items), 3)

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
from unittest import mock
from superdesk.tests import TestCase
from superdesk.io.feeding_services import http_base_service
from superdesk.io.feeding_services import ap
from superdesk.io.feed_parsers import newsml_2_0
from copy import deepcopy

PREFIX = "test_superdesk_"
PROVIDER = {
    "_id": "test_provider",
    "config": {
        "username": "user",
        "password": "password",
        "idList": "123",
        "feed_parser": "newsml2",
        "field_aliases": [],
    },
}


class APTestCase(TestCase):
    def setUp(self):
        super().setUp()
        with self.app.app_context():
            vocab = [{}]
            self.app.data.insert("vocabularies", vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", "ap.xml"))
        with open(fixture, "rb") as f:
            self.feed_raw = f.read()

    @mock.patch.object(http_base_service, "requests")
    @mock.patch.object(ap.APFeedingService, "get_feed_parser")
    def test_feeding(self, get_feed_parser, requests):
        get_feed_parser.return_value = newsml_2_0.NewsMLTwoFeedParser()
        mock_get = requests.get.return_value
        mock_get.content = self.feed_raw
        provider = deepcopy(PROVIDER)
        service = ap.APFeedingService()
        service.provider = provider
        items = service._update(provider, {})[0]
        self.assertEqual(len(items), 3)

    @mock.patch.object(http_base_service, "requests")
    @mock.patch.object(ap.APFeedingService, "get_feed_parser")
    def test_items_order(self, get_feed_parser, requests):
        """Test that items are reversed on first call (SDESK-4372)

        Items of a new provider must be in reverse chronological order
        while further updates should give chronological order
        so we check that "reverse" has been called on items to fix order
        on first call.
        """
        feed_parser = newsml_2_0.NewsMLTwoFeedParser()
        get_feed_parser.return_value = feed_parser
        mock_get = requests.get.return_value
        mock_get.content = self.feed_raw
        provider = deepcopy(PROVIDER)
        service = ap.APFeedingService()
        service.provider = provider

        self.assertNotIn("private", provider)
        with mock.patch.object(feed_parser, "parse"):
            update = {}
            items = service._update(provider, update)[0]
            items.reverse.assert_called_once_with()
            provider.update(update)

        # because the provider has been run at least one time,
        # private data must now be present
        self.assertIn("private", provider)
        with mock.patch.object(feed_parser, "parse"):
            items = service._update(provider, {})[0]
            items.reverse.assert_not_called()

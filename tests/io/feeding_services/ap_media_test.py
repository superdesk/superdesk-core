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
from httmock import urlmatch, HTTMock
import os
from superdesk.tests import TestCase
from superdesk.io.feeding_services import APMediaFeedingService
from superdesk.io.feed_parsers import APMediaFeedParser

PREFIX = 'test_superdesk_'
PROVIDER = {
    "_id": "test_provider",
    "config": {
        "api_url": "https://a.b.c/media/v/content/feed",
        "product_url": "https://api.ap.org/media/v/account/plans",
        "availableProducts": "12345",
        "apikey": "MYKEY",
        "productList": ""
    },
}


class APTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.setupMock(self)
#        with self.app.app_context():
#            vocab = [{}]
#            self.app.data.insert('vocabularies', vocab)

    def setupMock(self, context):
        context.mock = HTTMock(*[self.feed_request], *[self.item_request], *[self.text_feed_request],
                               *[self.text_item_request], *[self.nitf_item_request])
        context.mock.__enter__()

    @urlmatch(scheme='https', netloc='a.b.c', path='/media/v/content/feed')
    def feed_request(self, url, request):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ap_media_feed.json'))
        with open(fixture, 'r') as f:
            feed_raw = f.read()
        return {'status_code': 200, 'content': feed_raw}

    @urlmatch(scheme='https', netloc='a.b.c', path='/media/v/content/95e8bd71fed448cda1a0be35d8ddbd2f')
    def item_request(self, url, request):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ap_media_item.json'))
        with open(fixture, 'r') as f:
            feed_item = f.read()
        return {'status_code': 200, 'content': feed_item}

    @mock.patch.object(APMediaFeedingService, 'get_feed_parser')
    def test_feeding(self, get_feed_parser):
        get_feed_parser.return_value = APMediaFeedParser()
        provider = PROVIDER.copy()
        provider['config']['api_url'] = "https://a.b.c/media/v/content/feed"
        service = APMediaFeedingService()
        service.provider = provider
        items = service._update(provider, {})[0]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get('headline'), 'headline')

    @urlmatch(scheme='https', netloc='d.e.f', path='/media/v/content/feed')
    def text_feed_request(self, url, request):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ap_media_text_feed.json'))
        with open(fixture, 'r') as f:
            feed_raw = f.read()
        return {'status_code': 200, 'content': feed_raw}

    @urlmatch(scheme='https', netloc='a.b.c', path='/media/v/content/5ee9b4b40ea5fe9c9ca60f890fb2e1d9')
    def text_item_request(self, url, request):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ap_media_text_item.json'))
        with open(fixture, 'r') as f:
            feed_item = f.read()
        return {'status_code': 200, 'content': feed_item}

    @urlmatch(scheme='https', netloc='d.e.f', path='/media/v/content/5ee9b4b40ea5fe9c9ca60f890fb2e1d9.0/download')
    def nitf_item_request(self, url, request):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', 'ap_media_text_nitf.xml'))
        with open(fixture, 'r') as f:
            feed_item = f.read()
        return {'status_code': 200, 'content': feed_item}

    @mock.patch.object(APMediaFeedingService, 'get_feed_parser')
    def test_text_feeding(self, get_feed_parser):
        get_feed_parser.return_value = APMediaFeedParser()
        provider = PROVIDER.copy()
        provider['config']['api_url'] = "https://d.e.f/media/v/content/feed"
        provider['config']['next_link'] = ''
        service = APMediaFeedingService()
        service.provider = provider
        items = service._update(provider, {})[0]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get('headline'), 'BC-BBN--Top Ten')
        self.assertEqual(items[0].get('slugline'), 'BBN--Top Ten')
        self.assertEqual(items[0].get('subject'), [{'name': 'baseball', 'qcode': '15007000'}])

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
from superdesk.io.feed_parsers import wordpress_wxr
from unittest import mock
import datetime

FAKE_MEDIA_DATA = {'_created': datetime.datetime(2017, 4, 26, 13, 0, 33, tzinfo=datetime.timezone.utc),
                   '_etag': '0b135dc3959fe4b09642d02ae733b94af72af5d3',
                   '_id': '590099f1cc3a2d2349a785f4',
                   '_updated': datetime.datetime(2017, 4, 26, 13, 0, 33, tzinfo=datetime.timezone.utc),
                   'media': '590099f1cc3a2d2349a785ee',
                   'mimetype': 'image/jpeg',
                   'renditions': {'original': {'height': 256,
                                               'href': 'http://test',
                                               'media': '590099f1cc3a2d2349a785ee',
                                               'mimetype': 'image/jpeg',
                                               'width': 642},
                                  'thumbnail': {'height': 23,
                                                'href': 'http://test',
                                                'media': '590099f1cc3a2d2349a785f0',
                                                'mimetype': 'image/jpeg',
                                                'width': 60},
                                  'viewImage': {'height': 79,
                                                'href': 'http://test',
                                                'media': '590099f1cc3a2d2349a785f2',
                                                'mimetype': 'image/jpeg',
                                                'width': 200}}}


class FakeUploadService(object):

    def post(self, items):
        # we use URL as object_id so we can check the value easily
        return [items[0]['URL']]

    def get(self, req, lookup):
        media_data = FAKE_MEDIA_DATA
        media_data['_id'] = lookup['_id']
        return iter([media_data])


class WPWXRTestCase(TestCase):

    filename = 'wordpress_wxr.xml'

    @mock.patch.object(wordpress_wxr, 'get_resource_service', lambda _: FakeUploadService())
    def __init__(self, methodname):
        super().__init__(methodname)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture, 'rb') as f:
            buf = f.read()
        self.ori_file = buf
        buf = buf.replace(b'\r', b'&#13;')
        parser = etree.XMLParser(recover=True)
        parsed = etree.fromstring(buf, parser)
        self.articles = wordpress_wxr.WPWXRFeedParser().parse(parsed, provider)

    def test_guid(self):
        self.assertEqual(self.articles[0]['guid'], 'http://sdnewtester.org/?p=216')

    def test_versioncreated(self):
        self.assertEqual(self.articles[0]['versioncreated'],
                         datetime.datetime(2013, 7, 29, 16, 3, 54, tzinfo=datetime.timezone.utc))

    def test_author(self):
        self.assertEqual(self.articles[0]['author'], 'admin')

    def test_headline(self):
        self.assertEqual(self.articles[0]['headline'], 'Starafrica to dispose assets for $6 million to clear debt')

    def test_body_html(self):
        expected = ('<p>By Tester\nHarare, July 19 (The SDNewTester) - '
                    'Cash-strapped StarAfrica Corporation is set to dis'
                    'pose its transport company and its stake in Tongaa'
                    't Hulett Botswana for $6 million to offset part of'
                    ' the companyâs $19.7 million debt.\nBla bla test</p>')
        self.assertEqual(self.articles[0]['body_html'], expected)

    def test_keywords(self):
        self.assertEqual(self.articles[0]['keywords'], ['companies'])

    def test_category(self):
        self.assertEqual(self.articles[0]['anpa_category'],
                         [{'qcode': 'Business', 'qname': 'Business'},
                          {'qcode': 'Companies', 'qname': 'Companies'},
                          {'qcode': 'Economy', 'qname': 'Economy'}])

    def test_attachments(self):
        expected = {'_id': 'http://example.net/image.png',
                    'ingest_provider': 'wpwxr',
                    'headline': 'test2',
                    'alt_text': ' ',
                    'description_text': ' ',
                    'renditions': {'original': {'height': 256,
                                                'href': 'http://test',
                                                'media': '590099f1cc3a2d2349a785ee',
                                                'mimetype': 'image/jpeg',
                                                'width': 642},
                                   'thumbnail': {'height': 23,
                                                 'href': 'http://test',
                                                 'media': '590099f1cc3a2d2349a785f0',
                                                 'mimetype': 'image/jpeg',
                                                 'width': 60},
                                   'viewImage': {'height': 79,
                                                 'href': 'http://test',
                                                 'media': '590099f1cc3a2d2349a785f2',
                                                 'mimetype': 'image/jpeg',
                                                 'width': 200}},
                    'type': 'picture'}
        self.assertEqual(self.articles[1]['associations']['featuremedia'], expected)

    def test_clrf(self):
        expected = ('<p>By Tester</p><p>Harare, July 19 (The SDNewTester) - Cash-strapped'
                    ' StarAfrica Corporation is set to dispose its transport company and '
                    'its stake in Tongaat Hulett Botswana for $6 million to offset part o'
                    'f the companyâs $19.7 million debt.</p><hr><p>Bla bla test</p>')
        self.assertEqual(self.articles[2]['body_html'], expected)

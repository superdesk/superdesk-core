# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json

from unittest import mock
from datetime import timedelta

from superdesk.utc import utcnow
from superdesk.tests import TestCase
from superdesk.publish.formatters.ninjs_formatter import NINJSFormatter
from superdesk.publish import init_app


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class NinjsFormatterTest(TestCase):
    def setUp(self):
        self.formatter = NINJSFormatter()
        init_app(self.app)
        self.maxDiff = None

    def test_text_formatter(self):
        embargo_ts = (utcnow() + timedelta(days=2))
        article = {
            '_id': 'tag:aap.com.au:20150613:12345',
            'guid': 'tag:aap.com.au:20150613:12345',
            '_current_version': 1,
            'anpa_category': [{'qcode': 'a'}],
            'source': 'AAP',
            'headline': 'This is a test headline',
            'byline': 'joe',
            'slugline': 'slugline',
            'subject': [{'qcode': '02011001', 'name': 'international court or tribunal', 'parent': None},
                        {'qcode': '02011002', 'name': 'extradition'}],
            'anpa_take_key': 'take_key',
            'unique_id': '1',
            'body_html': 'The story body',
            'type': 'text',
            'word_count': '1',
            'priority': 1,
            'profile': 'snap',
            'state': 'published',
            'urgency': 2,
            'pubstatus': 'usable',
            'creditline': 'sample creditline',
            'keywords': ['traffic'],
            'abstract': '<p>sample <b>abstract</b></p>',
            'place': [{'name': 'Australia', 'qcode': 'NSW'}],
            'embargo': embargo_ts,
            'body_footer': '<p>call helpline 999 if you are planning to quit smoking</p>',
            'company_codes': [{'name': 'YANCOAL AUSTRALIA LIMITED', 'qcode': 'YAL', 'security_exchange': 'ASX'}],
            'genre': [{'name': 'Article', 'qcode': 'article'}],
            'flags': {'marked_for_legal': True},
        }
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "guid": "tag:aap.com.au:20150613:12345",
            "version": "1",
            "place": [{'name': 'Australia', 'code': 'NSW'}],
            "pubstatus": "usable",
            "body_html": "The story body<p>call helpline 999 if you are planning to quit smoking</p>",
            "type": "text",
            "subject": [{"code": "02011001", "name": "international court or tribunal"},
                        {"code": "02011002", "name": "extradition"}],
            "service": [{"code": "a"}],
            "source": "AAP",
            "headline": "This is a test headline",
            "byline": "joe",
            "urgency": 2,
            "priority": 1,
            "embargoed": embargo_ts.isoformat(),
            "profile": "snap",
            "slugline": "slugline",
            "description_text": "sample abstract",
            "description_html": "<p>sample <b>abstract</b></p>",
            'keywords': ['traffic'],
            'organisation': [{'name': 'YANCOAL AUSTRALIA LIMITED', 'rel': 'Securities Identifier',
                              'symbols': [{'ticker': 'YAL', 'exchange': 'ASX'}]}],
            'genre': [{'name': 'Article', 'code': 'article'}],
            'signal': [{'name': 'Content Warning', 'code': 'cwarn', 'scheme': 'http://cv.iptc.org/newscodes/signal/'}],
        }
        self.assertEqual(json.loads(doc), expected)

    def test_picture_formatter(self):
        article = {
            'guid': '20150723001158606583',
            '_current_version': 1,
            'slugline': "AMAZING PICTURE",
            'original_source': 'AAP',
            'renditions': {
                'viewImage': {
                    'width': 640,
                    'href': 'http://localhost:5000/api/upload/55b032041d41c8d278d21b6f/raw?_schema=http',
                    'mimetype': 'image/jpeg',
                    "height": 401
                },
                'original': {
                    'href': 'https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download',
                    'mimetype': 'image/jpeg'
                },
            },
            'byline': 'MICKEY MOUSE',
            'headline': 'AMAZING PICTURE',
            'versioncreated': '2015-07-23T00:15:00.000Z',
            'ednote': 'TEST ONLY',
            'type': 'picture',
            'pubstatus': 'usable',
            'source': 'AAP',
            'description': 'The most amazing picture you will ever see',
            'guid': '20150723001158606583',
            'body_footer': '<p>call helpline 999 if you are planning to quit smoking</p>'
        }
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "original": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download",
                    "mimetype": "image/jpeg"
                },
            },
            "headline": "AMAZING PICTURE",
            "pubstatus": "usable",
            "version": "1",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "guid": "20150723001158606583",
            "description_html":
            "The most amazing picture you will ever see<p>call helpline 999 if you are planning to quit smoking</p>",
            "type": "picture",
            "priority": 5,
            "slugline": "AMAZING PICTURE",
            'ednote': 'TEST ONLY',
            'source': 'AAP',
        }
        self.assertEqual(expected, json.loads(doc))

    def test_composite_formatter(self):
        article = {
            'guid': 'urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c',
            'groups': [
                {
                    'id': 'root',
                    'refs': [
                        {
                            'idRef': 'main'
                        },
                        {
                            'idRef': 'sidebars'
                        }
                    ],
                    'role': 'grpRole:NEP'
                },
                {
                    'id': 'main',
                    'refs': [
                        {
                            'renditions': {},
                            'slugline': 'Boat',
                            'guid': 'tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916',
                            'headline': 'WA:Navy steps in with WA asylum-seeker boat',
                            'location': 'archive',
                            'type': 'text',
                            'itemClass': 'icls:text',
                            'residRef': 'tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916'
                        }
                    ],
                    'role': 'grpRole:main'
                },
                {
                    'id': 'sidebars',
                    'refs': [
                        {
                            'renditions': {
                                'original_source': {
                                    'href':
                                        'https://one-api.aap.com.au\
                                        /api/v3/Assets/20150723001158639795/Original/download',
                                    'mimetype': 'image/jpeg'
                                },
                                'original': {
                                    'width': 2784,
                                    'height': 4176,
                                    'href': 'http://localhost:5000\
                                    /api/upload/55b078b21d41c8e974d17ec5/raw?_schema=http',
                                    'mimetype': 'image/jpeg',
                                    'media': '55b078b21d41c8e974d17ec5'
                                },
                                'thumbnail': {
                                    'width': 80,
                                    'height': 120,
                                    'href': 'http://localhost:5000\
                                    /api/upload/55b078b41d41c8e974d17ed3/raw?_schema=http',
                                    'mimetype': 'image/jpeg',
                                    'media': '55b078b41d41c8e974d17ed3'
                                },
                                'viewImage': {
                                    'width': 426,
                                    'height': 640,
                                    'href': 'http://localhost:5000\
                                    /api/upload/55b078b31d41c8e974d17ed1/raw?_schema=http',
                                    'mimetype': 'image/jpeg',
                                    'media': '55b078b31d41c8e974d17ed1'
                                },
                                'baseImage': {
                                    'width': 933,
                                    'height': 1400,
                                    'href': 'http://localhost:5000\
                                    /api/upload/55b078b31d41c8e974d17ecf/raw?_schema=http',
                                    'mimetype': 'image/jpeg',
                                    'media': '55b078b31d41c8e974d17ecf'
                                }
                            },
                            'slugline': 'ABC SHOP CLOSURES',
                            'type': 'picture',
                            'guid':
                                'urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164',
                            'headline': 'ABC SHOP CLOSURES',
                            'location': 'archive',
                            'itemClass': 'icls:picture',
                            'residRef':
                                'urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164'
                        }
                    ],
                    'role': 'grpRole:sidebars'
                }
            ],
            'description': '',
            'operation': 'update',
            'sign_off': 'mar',
            'type': 'composite',
            'pubstatus': 'usable',
            'version_creator': '558379451d41c83ff598a3af',
            'language': 'en',
            'guid': 'urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c',
            'unique_name': '#145',
            'headline': 'WA:Navy steps in with WA asylum-seeker boat',
            'original_creator': '558379451d41c83ff598a3af',
            'source': 'AAP',
            '_etag': 'b41df79084304219524a092abf07ecba9e1bb2c5',
            'slugline': 'Boat',
            'firstcreated': '2015-07-24T05:05:00.000Z',
            'unique_id': 145,
            'versioncreated': '2015-07-24T05:05:14.000Z',
            '_updated': '2015-07-24T05:05:25.000Z',
            'family_id': 'urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c',
            '_current_version': 2,
            '_created': '2015-07-24T05:05:00.000Z',
            'version': 2,
        }

        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "headline": "WA:Navy steps in with WA asylum-seeker boat",
            "version": "2",
            "guid": "urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c",
            "associations": {
                "main": {
                    "guid": "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916", "type": "text"
                },
                "sidebars": {
                    "guid": "urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164",
                    "type": "picture"
                }
            },
            'firstcreated': '2015-07-24T05:05:00.000Z',
            "versioncreated": "2015-07-24T05:05:14.000Z",
            "type": "composite",
            "pubstatus": "usable",
            "language": "en",
            "priority": 5,
            "slugline": "Boat",
            'source': 'AAP',
        }
        self.assertEqual(expected, json.loads(doc))

    def test_item_with_usable_associations(self):
        article = {
            '_id': 'urn:bar',
            'guid': 'urn:bar',
            '_current_version': 1,
            'type': 'text',
            'associations': {
                'image': {
                    '_id': 'urn:foo',
                    'guid': 'urn:foo',
                    'pubstatus': 'usable',
                    'headline': 'Foo',
                    'type': 'picture',
                    'task': {},
                    'copyrightholder': 'Foo ltd.',
                    'description_text': 'Foo picture',
                    'renditions': {
                        'original': {
                            'href': 'http://example.com',
                            'width': 100,
                            'height': 80,
                            'mimetype': 'image/jpeg',
                            'CropLeft': 0,
                        }
                    }
                }
            }
        }

        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        formatted = json.loads(doc)
        self.assertIn('associations', formatted)
        self.assertIn('image', formatted['associations'])
        image = formatted['associations']['image']
        self.assertEqual('urn:foo', image['guid'])
        self.assertEqual('Foo', image['headline'])
        self.assertEqual('usable', image['pubstatus'])
        self.assertNotIn('task', image)
        self.assertEqual('Foo ltd.', image['copyrightholder'])
        self.assertEqual('Foo picture', image['description_text'])
        rendition = image['renditions']['original']
        self.assertEqual(100, rendition['width'])
        self.assertEqual(80, rendition['height'])
        self.assertEqual('image/jpeg', rendition['mimetype'])
        self.assertNotIn('CropLeft', rendition)

    def test_vidible_formatting(self):
        article = {
            '_id': 'tag:aap.com.au:20150613:12345',
            'guid': 'tag:aap.com.au:20150613:12345',
            '_current_version': 1,
            'source': 'AAP',
            'headline': 'This is a test headline',
            'slugline': 'slugline',
            'unique_id': '1',
            'body_html': 'The story body',
            'type': 'text',
            'state': 'published',
            'pubstatus': 'usable',
            'associations': {
                "embedded5346670761": {
                    "uri": "56ba77bde4b0568f54a1ce68",
                    "alt_text": "alternative",
                    "copyrightholder": "Edouard",
                    "copyrightnotice": "Edited with Gimp",
                    "usageterms": "indefinite-usage",
                    "type": "video",
                    "title": "Embed title",
                    "company": "Press Association",
                    "url": "https://videos.vidible.tv/prod/2016-02/09/56ba777ce4b0b6448ed478f5_640x360.mp4",
                    "thumbnail": "https://cdn-ssl.vidible.tv/2016-02/09/56ba777ce4b0b6448ed478f5_60x60.jpg",
                    "duration": 100,
                    "width": 400,
                    "height": 200
                }
            }
        }
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "guid": "tag:aap.com.au:20150613:12345",
            "version": "1",
            "pubstatus": "usable",
            "body_html": "The story body",
            "type": "text",
            "headline": "This is a test headline",
            "slugline": "slugline",
            "priority": 5,
            'source': 'AAP',
            'associations': {
                "embedded5346670761": {
                    "guid": "56ba77bde4b0568f54a1ce68",
                    "type": "video",
                    "version": "1",
                    "priority": 5,
                    "body_text": "alternative",
                    "copyrightholder": "Edouard",
                    "copyrightnotice": "Edited with Gimp",
                    "usageterms": "indefinite-usage",
                    "headline": "Embed title",
                    "organisation": [{"name": "Press Association"}],
                    "renditions": {
                        "original": {
                            "href": "https://videos.vidible.tv/prod/2016-02/09/56ba777ce4b0b6448ed478f5_640x360.mp4",
                            "duration": 100,
                            "width": 400,
                            "height": 200
                        },
                        "thumbnail": {
                            "href": "https://cdn-ssl.vidible.tv/2016-02/09/56ba777ce4b0b6448ed478f5_60x60.jpg"
                        }
                    }
                }
            }
        }
        self.assertEqual(json.loads(doc), expected)

    def test_copyright_holder_notice(self):
        self.app.data.insert('vocabularies', [{'_id': 'rightsinfo', 'items': [
            {
                "is_active": True,
                "name": "default",
                "copyrightHolder": "copyright holder",
                "copyrightNotice": "copyright notice",
                "usageTerms": ""
            }
        ]}])

        article = {
            '_id': 'urn:bar',
            '_current_version': 1,
            'guid': 'urn:bar',
            'type': 'text',
        }

        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        data = json.loads(doc)

        self.assertEqual('copyright holder', data['copyrightholder'])
        self.assertEqual('copyright notice', data['copyrightnotice'])
        self.assertEqual('', data['usageterms'])

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from unittest import mock
from datetime import timedelta
import json

from superdesk.utc import utcnow
from superdesk.tests import TestCase
from superdesk.publish.formatters.ninjs_formatter import NINJSFormatter
from superdesk.publish import init_app


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class NinjsFormatterTest(TestCase):
    def setUp(self):
        super().setUp()
        self.formatter = NINJSFormatter()
        init_app(self.app)
        self.maxDiff = None

    def test_text_formatter(self):
        embargo_ts = (utcnow() + timedelta(days=2))
        article = {
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
            '_id': 'urn:localhost.abc',
            'state': 'published',
            'urgency': 2,
            'pubstatus': 'usable',
            'creditline': 'sample creditline',
            'keywords': ['traffic'],
            'abstract': 'sample abstract',
            'place': 'Australia',
            'embargo': embargo_ts,
            'body_footer': 'call helpline 999 if you are planning to quit smoking',
            'company_codes': [{'name': 'YANCOAL AUSTRALIA LIMITED', 'qcode': 'YAL', 'security_exchange': 'ASX'}]
        }
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "version": "1",
            "place": "Australia",
            "pubstatus": "usable",
            "body_html": "The story body<br>call helpline 999 if you are planning to quit smoking",
            "type": "text",
            "subject": [{"code": "02011001", "name": "international court or tribunal"},
                        {"code": "02011002", "name": "extradition"}],
            "service": [{"code": "a"}],
            "headline": "This is a test headline",
            "byline": "joe",
            "_id": "urn:localhost.abc",
            "urgency": 2,
            "priority": 1,
            "embargoed": embargo_ts.isoformat(),
            "profile": "snap",
            "slugline": "slugline",
            "description_text": "sample abstract",
            'keywords': ['traffic'],
            'organisation': [{'name': 'YANCOAL AUSTRALIA LIMITED', 'rel': 'Securities Identifier',
                              'symbols': [{'ticker': 'YAL', 'exchange': 'ASX'}]}]
        }
        self.assertEqual(json.loads(doc), expected)

    def test_picture_formatter(self):
        article = {
            '_id': '20150723001158606583',
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
                'original_source': {
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
            'body_footer': 'call helpline 999 if you are planning to quit smoking'
        }
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "viewImage": {
                    "href": "http://localhost:5000/api/upload/55b032041d41c8d278d21b6f/raw?_schema=http",
                    "mimetype": "image/jpeg",
                    "width": 640,
                    "height": 401
                },
                "original_source": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download",
                    "mimetype": "image/jpeg"
                },
            },
            "headline": "AMAZING PICTURE",
            "pubstatus": "usable",
            "version": "1",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "_id": "20150723001158606583",
            "description_html":
                "The most amazing picture you will ever see<br>call helpline 999 if you are planning to quit smoking",
            "type": "picture",
            "priority": 5,
            "slugline": "AMAZING PICTURE",
        }
        self.assertEqual(expected, json.loads(doc))

    def test_composite_formatter(self):
        article = {
            '_id': 'urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c',
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
            "_id": "urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c",
            "associations": {
                "main": [
                    {"_id": "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916", "type": "text"}
                ],
                "sidebars": [
                    {
                        "_id": "urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164",
                        "type": "picture"
                    }
                ]
            },
            "versioncreated": "2015-07-24T05:05:14.000Z",
            "type": "composite",
            "pubstatus": "usable",
            "language": "en",
            "priority": 5,
            "slugline": "Boat",
        }
        self.assertEqual(expected, json.loads(doc))

    def test_item_with_usable_associations(self):
        article = {
            '_id': 'urn:bar',
            '_current_version': 1,
            'type': 'text',
            'associations': {
                'image': {
                    '_id': 'foo',
                    'guid': 'urn:foo',
                    'pubstatus': 'usable',
                    'headline': 'Foo',
                    'type': 'picture',
                    'task': {},
                    'copyrightholder': 'Foo ltd.',
                    'description_text': 'Foo picture',
                    'renditions': {
                        'thumbnail': {
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
        self.assertEqual('foo', image['_id'])
        self.assertEqual('Foo', image['headline'])
        self.assertEqual('usable', image['pubstatus'])
        self.assertNotIn('task', image)
        self.assertEqual('Foo ltd.', image['copyrightholder'])
        self.assertEqual('Foo picture', image['description_text'])
        rendition = image['renditions']['thumbnail']
        self.assertEqual(100, rendition['width'])
        self.assertEqual(80, rendition['height'])
        self.assertEqual('image/jpeg', rendition['mimetype'])
        self.assertNotIn('CropLeft', rendition)

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
from superdesk.publish.formatters.ninjs_newsroom_formatter import NewsroomNinjsFormatter
from superdesk.publish import init_app

import planning.assignments as planning_assignments
import planning.planning as planning_planning


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class NewsroomNinjsFormatterTest(TestCase):
    def setUp(self):
        self.formatter = NewsroomNinjsFormatter()
        init_app(self.app)
        self.maxDiff = None

    def test_products(self):
        self.app.data.insert('content_filters',
                             [{"_id": 3,
                               "content_filter": [{"expression": {"pf": [1], "fc": [2]}}],
                               "name": "soccer-only3"}])
        self.app.data.insert('filter_conditions',
                             [{'_id': 1,
                               'field': 'headline',
                               'operator': 'like',
                               'value': 'test',
                               'name': 'test-1'}])
        self.app.data.insert('filter_conditions',
                             [{'_id': 2,
                               'field': 'urgency',
                               'operator': 'in',
                               'value': '2',
                               'name': 'test-2'}])
        self.app.data.insert('products',
                             [{"_id": 1,
                               "content_filter": {"filter_id": 3, "filter_type": "permitting"},
                               "name": "p-1", "product_type": "api"}])
        self.app.data.insert('vocabularies', [
            {
                "_id": "locators",
                "display_name": "Locators",
                "type": "unmanageable",
                "unique_field": "qcode",
                "items": [
                    {"is_active": True, "name": "NSW", "qcode": "NSW", "state": "New South Wales",
                     "country": "Australia", "world_region": "Oceania", "group": "Australia"},
                ],
            }
        ])
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
            'place': [{'name': 'NSW', 'qcode': 'NSW'}],
            'embargo': embargo_ts,
            'body_footer': '<p>call helpline 999 if you are planning to quit smoking</p>',
            'company_codes': [{'name': 'YANCOAL AUSTRALIA LIMITED', 'qcode': 'YAL', 'security_exchange': 'ASX'}],
            'genre': [{'name': 'Article', 'qcode': 'article'}],
            'flags': {'marked_for_legal': True},
            'extra': {'foo': 'test'},
            'operation': 'publish'
        }
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "guid": "tag:aap.com.au:20150613:12345",
            "version": "1",
            "place": [{"code": "NSW", "name": "New South Wales"}],
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
            'extra': {'foo': 'test'},
            'charcount': 67,
            'wordcount': 13,
            'readtime': 0,
            'products': [{'code': 1, 'name': 'p-1'}]
        }
        self.assertEqual(json.loads(doc), expected)
        article['urgency'] = 1
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        expected = {
            "guid": "tag:aap.com.au:20150613:12345",
            "version": "1",
            "place": [{"code": "NSW", "name": "New South Wales"}],
            "pubstatus": "usable",
            "body_html": "The story body<p>call helpline 999 if you are planning to quit smoking</p>",
            "type": "text",
            "subject": [{"code": "02011001", "name": "international court or tribunal"},
                        {"code": "02011002", "name": "extradition"}],
            "service": [{"code": "a"}],
            "source": "AAP",
            "headline": "This is a test headline",
            "byline": "joe",
            "urgency": 1,
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
            'extra': {'foo': 'test'},
            'charcount': 67,
            'wordcount': 13,
            'readtime': 0,
            'products': []
        }
        self.assertEqual(json.loads(doc), expected)

    def test_planning_data(self):
        planning_assignments.init_app(self.app)
        planning_planning.init_app(self.app)

        assignments = [{'coverage_item': 'urn:coverage-id', 'planning_item': 'urn:planning-id'}]
        self.app.data.insert('assignments', assignments)

        article = {
            '_id': 'tag:aap.com.au:20150613:12345',
            'guid': 'tag:aap.com.au:20150613:12345',
            'type': 'text',
            'version': 1,
            'assignment_id': assignments[0]['_id'],
        }

        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        data = json.loads(doc)

        self.assertEqual('urn:planning-id', data['planning_id'])
        self.assertEqual('urn:coverage-id', data['coverage_id'])

    def test_picture_formatter(self):
        article = {
            "guid": "20150723001158606583",
            "_current_version": 1,
            "slugline": "AMAZING PICTURE",
            "original_source": "AAP",
            "renditions": {
                "viewImage": {
                    "width": 640,
                    "href": "http://localhost:5000/api/upload/55b032041d41c8d278d21b6f/raw?_schema=http",
                    "mimetype": "image/jpeg",
                    "height": 401,
                },
                "original": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download",
                    "mimetype": "image/jpeg",
                },
            },
            "byline": "MICKEY MOUSE",
            "headline": "AMAZING PICTURE",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "ednote": "TEST ONLY",
            "type": "picture",
            "pubstatus": "usable",
            "source": "AAP",
            "description": "The most amazing picture you will ever see",
            "guid": "20150723001158606583",
            "body_footer": "<p>call helpline 999 if you are planning to quit smoking</p>",
        }
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "original": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download",
                    "mimetype": "image/jpeg",
                },
                "viewImage": {
                    "href": "http://localhost:5000/api/upload/55b032041d41c8d278d21b6f/raw?_schema=http",
                    "mimetype": "image/jpeg",
                    "width": 640,
                    "height": 401,
                }
            },
            "headline": "AMAZING PICTURE",
            "pubstatus": "usable",
            "version": "1",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "guid": "20150723001158606583",
            "description_html": "The most amazing picture you will ever see<p>call helpline 999 if you are planning to "
            "quit smoking</p>",
            "type": "picture",
            "priority": 5,
            "slugline": "AMAZING PICTURE",
            "ednote": "TEST ONLY",
            "source": "AAP",
            "products": [],
        }
        self.assertEqual(expected, json.loads(doc))
        self.assertIn('viewImage', json.loads(doc).get('renditions'))

    def test_auto_published_item(self):
        article = {
            "guid": "foo",
            "_current_version": 1,
            "slugline": "AMAZING PICTURE",
            "original_source": "AAP",
            "byline": "MICKEY MOUSE",
            "headline": "AMAZING PICTURE",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "ednote": "TEST ONLY",
            "type": "picture",
            "pubstatus": "usable",
            "source": "AAP",
            "description": "The most amazing picture you will ever see",
            "body_footer": "<p>call helpline 999 if you are planning to quit smoking</p>",
        }
        _, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        processed = json.loads(doc)
        self.assertEqual(processed['guid'], 'foo')
        article['ingest_id'] = 'bar'
        article['ingest_version'] = '7'
        _, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        processed = json.loads(doc)
        self.assertEqual(processed['guid'], 'foo')
        article['auto_publish'] = True
        _, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        processed = json.loads(doc)
        self.assertEqual(processed['guid'], 'bar')
        self.assertEqual(processed['version'], '7')

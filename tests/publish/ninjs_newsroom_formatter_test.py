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


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class NinjsFormatterTest(TestCase):
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

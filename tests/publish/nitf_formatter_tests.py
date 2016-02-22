# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from unittest import mock
from superdesk.publish.formatters.nitf_formatter import NITFFormatter
from superdesk.publish.formatters import Formatter
from superdesk.publish import init_app
import xml.etree.ElementTree as etree


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class NitfFormatterTest(TestCase):
    def setUp(self):
        super().setUp()
        self.formatter = NITFFormatter()
        self.base_formatter = Formatter()
        init_app(self.app)

    def test_append_legal(self):
        article = {
            'slugline': 'Obama Republican Healthc',
            'flags': {'marked_for_legal': True}
        }

        slugline = self.base_formatter.append_legal(article)
        self.assertEqual(slugline, 'Legal: Obama Republican Healthc')
        slugline = self.base_formatter.append_legal(article, truncate=True)
        self.assertEqual(slugline, 'Legal: Obama Republican ')

    def test_append_legal_when_not_legal(self):
        article = {
            'slugline': 'Obama Republican Healthc',
            'flags': {'marked_for_legal': False}
        }

        slugline = self.base_formatter.append_legal(article)
        self.assertEqual(slugline, 'Obama Republican Healthc')

    def test_company_codes(self):
        article = {
            'guid': 'tag:aap.com.au:20150613:12345',
            '_current_version': 1,
            'anpa_category': [{'qcode': 'f', 'name': 'Finance'}],
            'source': 'AAP',
            'headline': 'This is a test headline',
            'byline': 'joe',
            'slugline': 'slugline',
            'subject': [{'qcode': '02011001', 'name': 'international court or tribunal'},
                        {'qcode': '02011002', 'name': 'extradition'}],
            'anpa_take_key': 'take_key',
            'unique_id': '1',
            'body_html': 'The story body',
            'type': 'text',
            'word_count': '1',
            'priority': '1',
            '_id': 'urn:localhost.abc',
            'state': 'published',
            'urgency': 2,
            'pubstatus': 'usable',
            'dateline': {
                'source': 'AAP',
                'text': 'Los Angeles, Aug 11 AAP -',
                'located': {
                    'alt_name': '',
                    'state': 'California',
                    'city_code': 'Los Angeles',
                    'city': 'Los Angeles',
                    'dateline': 'city',
                    'country_code': 'US',
                    'country': 'USA',
                    'tz': 'America/Los_Angeles',
                    'state_code': 'CA'
                }
            },
            'creditline': 'sample creditline',
            'keywords': ['traffic'],
            'abstract': 'sample abstract',
            'place': [{'qcode': 'Australia', 'name': 'Australia',
                       'state': '', 'country': 'Australia',
                       'world_region': 'Oceania'}],
            'company_codes': [{'name': 'YANCOAL AUSTRALIA LIMITED', 'qcode': 'YAL', 'security_exchange': 'ASX'}]
        }

        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        nitf_xml = etree.fromstring(doc)
        company = nitf_xml.find('body/body.head/org')
        self.assertEqual(company.text, 'YANCOAL AUSTRALIA LIMITED')
        self.assertEqual(company.attrib.get('idsrc', ''), 'ASX')
        self.assertEqual(company.attrib.get('value', ''), 'YAL')

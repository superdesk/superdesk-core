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
from textwrap import dedent


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class NitfFormatterTest(TestCase):
    def setUp(self):
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

    def test_formatter(self):
        article = {
            'headline': 'test headline',
            'body_html': '<p>test body</p>',
            'type': 'text',
            'priority': '1',
            '_id': 'urn:localhost.abc',
            'urgency': 2
        }

        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        nitf_xml = etree.fromstring(doc)
        self.assertEqual(nitf_xml.find('head/title').text, article['headline'])
        self.assertEqual(nitf_xml.find('body/body.content/p').text, 'test body')
        self.assertEqual(nitf_xml.find('head/docdata/urgency').get('ed-urg'), '2')

    def test_html2nitf(self):
        html = etree.fromstring(dedent("""\
            <div>
                <unknown>
                    <p>
                        this should be still here
                    </p>
                </unknown>
                <p style="this='is';some='style'">
                    <strong>this text should be
                        <i>modified</i>
                    </strong>
                    so
                    <span>[this should not be removed]</span>
                    unkown
                    <em unknown_attribute="toto">elements</em>
                    and
                    <a bad_attribute="to_remove">attributes</a>
                    are
                    <h6>removed</h6>
                </p>
            </div>
            """))

        nitf = self.formatter.html2nitf(html, attr_remove=['style'])

        expected = dedent("""\
            <div>
                    <p>
                        this should be still here
                    </p>
                <p>
                    <em class="bold">this text should be
                        <em class="italic">modified</em>
                    </em>
                    so [this should not be removed] unkown
                    <em class="italic">elements</em>
                    and
                    <a>attributes</a>
                    are
                    <hl2>removed</hl2>
                </p>
            </div>""").replace('\n', '').replace(' ', '')
        self.assertEqual(etree.tostring(nitf, 'unicode').replace('\n', '').replace(' ', ''), expected)

    def test_table(self):
        html_raw = """
        <div>
        <table>
            <tbody>
                <tr>
                    <td>Table cell 1</td>
                    <td>Table cell 2</td>
                    <td>Table cell 3</td>
                </tr>
                <tr>
                    <td>Table cell 2.1</td>
                    <td>Table cell 2.2</td>
                    <td>Table cell 2.3</td>
                </tr>
                <tr>
                    <td>Table cell 3.1</td>
                    <td>Table cell 3.2</td>
                    <td>Table cell 3.3</td>
                </tr>
            </tbody>
        </table>
        </div>
        """.replace('\n', '').replace(' ', '')
        html = etree.fromstring(html_raw)
        nitf = self.formatter.html2nitf(html)
        self.assertEqual(etree.tostring(nitf, 'unicode'), html_raw)

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

    def testNoneAsciNamesContent(self):
        article = {
            '_id': '3',
            'source': 'AAP',
            'anpa_category': [{'qcode': 'a'}],
            'headline': 'This is a test headline',
            'byline': 'joe',
            'slugline': 'slugline',
            'subject': [{'qcode': '02011001'}],
            'anpa_take_key': 'take_key',
            'unique_id': '1',
            'type': 'text',
            'body_html': '<p>Tommi Mäkinen crashes a Škoda in Äppelbo</p>',
            'word_count': '1',
            'priority': 1,
            "linked_in_packages": [
                {
                    "package": "package",
                    "package_type": "takes"
                }
            ],
        }
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        nitf_xml = etree.fromstring(doc)
        self.assertEqual(nitf_xml.find('body/body.content/p').text, 'Tommi Mäkinen crashes a Škoda in Äppelbo')

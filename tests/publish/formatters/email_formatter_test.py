# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import json
import datetime
from unittest import mock

from superdesk.publish import init_app
from superdesk.publish.formatters.email_formatter import EmailFormatter
from superdesk.tests import TestCase
from superdesk.utc import utc


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class EmailFormatterTest(TestCase):
    def setUp(self):
        self.formatter = EmailFormatter()
        # self.base_formatter = Formatter()
        init_app(self.app)

    def test_formatter(self):
        article = {
            'source': 'AAP',
            'headline': 'This is a test headline',
            'abstract': 'Can of beans',
            'byline': 'joe',
            'ednote': 'Very good story',
            'dateline': {'text': 'BERN, July 13  -'},
            'slugline': 'slugline',
            'anpa_take_key': 'take',
            'subject': [{'qcode': '02011001'}],
            'format': 'HTML',
            'type': 'text',
            'body_html': '<p>The story body of the story so far</p>',
            'word_count': '1',
            'priority': 1,
            'place': [{'qcode': 'VIC', 'name': 'VIC'}],
            'genre': [],
            'sign_off': 'aa/bb'
        }

        article['versioncreated'] = datetime.datetime(year=2015, month=1, day=30, hour=2, minute=40, second=56,
                                                      tzinfo=utc)
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        item = json.loads(doc)
        self.assertEqual(item['message_subject'], 'This is a test headline')
        self.assertEqual(item['message_html'], '<html>\n<body>\n<h1>VIC:&nbsp;This is a test headline</h1>\n'
                                               'Published At : Fri Jan 30 03:40:56 2015\n<br>\n<b>slugline'
                                               '</b>&nbsp;take&nbsp;\n'
                                               '<hr>\n<br><font color="red">Very good story</font>'
                                               '<br>\n<i>Can of beans</i>\n<br>joe\n<br>\n'
                                               '<p>BERN, July 13  - The story body of the story so far</p>\n<br>\n'
                                               'AAP&nbsp;aa/bb\n\n</body>\n</html>')
        self.assertEqual(item['message_text'], 'VIC: This is a test headline\nPublished At : Fri Jan 30 03:40:56 2015\n'
                                               'slugline take\nVery good story\n------------------------------------'
                                               '----------------------\nCan of beans\n\njoe\nBERN, July 13  - The story'
                                               ' body of the story so far\n\nAAP aa/bb\n')

    def test_preserved_formatter(self):
        article = {
            'source': 'AAP',
            'headline': 'This is a test headline',
            'abstract': 'Can of beans',
            'byline': 'joe',
            'dateline': {'text': 'BERN, July 13  -'},
            'slugline': 'slugline',
            'anpa_take_key': 'take',
            'subject': [{'qcode': '02011001'}],
            'format': 'preserved',
            'type': 'text',
            'body_html': 'The story body of the story so far',
            'word_count': '1',
            'priority': 1,
            'place': [{'qcode': 'VIC', 'name': 'VIC'}],
            'genre': [],
            'sign_off': 'aa/bb'
        }

        article['versioncreated'] = datetime.datetime(year=2015, month=1, day=30, hour=2, minute=40, second=56,
                                                      tzinfo=utc)
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        item = json.loads(doc)
        self.assertEqual(item['message_subject'], 'This is a test headline')
        self.assertEqual(item['message_html'], None)

    def test_no_place_formatter(self):
        article = {
            'source': 'AAP',
            'headline': 'This is a test headline',
            'abstract': 'Can of beans',
            'byline': 'joe',
            'ednote': 'Very good story',
            'dateline': {'text': 'BERN, July 13  -'},
            'slugline': 'slugline',
            'anpa_take_key': 'take',
            'subject': [{'qcode': '02011001'}],
            'format': 'HTML',
            'type': 'text',
            'body_html': '<p>The story body of the story so far</p>',
            'word_count': '1',
            'priority': 1,
            'genre': [],
            'sign_off': 'aa/bb'
        }

        article['versioncreated'] = datetime.datetime(year=2015, month=1, day=30, hour=2, minute=40, second=56,
                                                      tzinfo=utc)
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        item = json.loads(doc)
        self.assertEqual(item['message_subject'], 'This is a test headline')
        self.assertEqual(item['message_html'], '<html>\n<body>\n<h1>This is a test headline</h1>\n'
                                               'Published At : Fri Jan 30 03:40:56 2015\n<br>\n<b>slugline'
                                               '</b>&nbsp;take&nbsp;\n'
                                               '<hr>\n<br><font color="red">Very good story</font>'
                                               '<br>\n<i>Can of beans</i>\n<br>joe\n<br>\n'
                                               '<p>BERN, July 13  - The story body of the story so far</p>\n<br>\n'
                                               'AAP&nbsp;aa/bb\n\n</body>\n</html>')
        self.assertEqual(item['message_text'], 'This is a test headline\nPublished At : Fri Jan 30 03:40:56 2015\n'
                                               'slugline take\nVery good story\n------------------------------------'
                                               '----------------------\nCan of beans\n\njoe\nBERN, July 13  - The story'
                                               ' body of the story so far\n\nAAP aa/bb\n')

    def test_none_place_formatter(self):
        article = {
            'source': 'AAP',
            'headline': 'This is a test headline',
            'abstract': 'Can of beans',
            'byline': 'joe',
            'ednote': 'Very good story',
            'dateline': {'text': 'BERN, July 13  -'},
            'slugline': 'slugline',
            'anpa_take_key': 'take',
            'subject': [{'qcode': '02011001'}],
            'format': 'HTML',
            'type': 'text',
            'body_html': '<p>The story body of the story so far</p>',
            'word_count': '1',
            'priority': 1,
            'place': None,
            'genre': [],
            'sign_off': 'aa/bb'
        }

        article['versioncreated'] = datetime.datetime(year=2015, month=1, day=30, hour=2, minute=40, second=56,
                                                      tzinfo=utc)
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        item = json.loads(doc)
        self.assertEqual(item['message_subject'], 'This is a test headline')
        self.assertEqual(item['message_html'], '<html>\n<body>\n<h1>This is a test headline</h1>\n'
                                               'Published At : Fri Jan 30 03:40:56 2015\n<br>\n<b>slugline'
                                               '</b>&nbsp;take&nbsp;\n'
                                               '<hr>\n<br><font color="red">Very good story</font>'
                                               '<br>\n<i>Can of beans</i>\n<br>joe\n<br>\n'
                                               '<p>BERN, July 13  - The story body of the story so far</p>\n<br>\n'
                                               'AAP&nbsp;aa/bb\n\n</body>\n</html>')
        self.assertEqual(item['message_text'], 'This is a test headline\nPublished At : Fri Jan 30 03:40:56 2015\n'
                                               'slugline take\nVery good story\n------------------------------------'
                                               '----------------------\nCan of beans\n\njoe\nBERN, July 13  - The'
                                               ' story body of the story so far\n\nAAP aa/bb\n')

    def test_none_takekey_ednote(self):
        article = {
            'source': 'AAP',
            'headline': 'This is a test headline',
            'abstract': 'Can of beans',
            'byline': 'joe',
            'ednote': None,
            'dateline': {'text': 'BERN, July 13  -'},
            'slugline': 'slugline',
            'anpa_take_key': None,
            'subject': [{'qcode': '02011001'}],
            'format': 'HTML',
            'type': 'text',
            'body_html': '<p>The story body of the story so far</p>',
            'word_count': '1',
            'priority': 1,
            'place': None,
            'genre': [],
            'sign_off': 'aa/bb'
        }

        article['versioncreated'] = datetime.datetime(year=2015, month=1, day=30, hour=2, minute=40, second=56,
                                                      tzinfo=utc)
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        item = json.loads(doc)
        self.assertEqual(item['message_subject'], 'This is a test headline')
        self.assertEqual(item['message_html'], '<html>\n<body>\n<h1>This is a test headline</h1>\n'
                                               'Published At : Fri Jan 30 03:40:56 2015\n<br>\n<b>slugline'
                                               '</b>&nbsp;\n<hr>\n'
                                               '\n<i>Can of beans</i>\n<br>joe\n<br>\n'
                                               '<p>BERN, July 13  - The story body of the story so far</p>\n<br>\n'
                                               'AAP&nbsp;aa/bb\n\n</body>\n</html>')
        self.assertEqual(item['message_text'], 'This is a test headline\nPublished At : Fri Jan 30 03:40:56 2015\n'
                                               'slugline \n\n------------------------------------'
                                               '----------------------\nCan of beans\n\njoe\nBERN, July 13  - The story'
                                               ' body of the story so far\n\nAAP aa/bb\n')

    def test_subject_cyrilic(self):
        article = {'headline': 'Неправильная музыка Джамала Али'}
        seq, doc = self.formatter.format(article, {'name': 'Test'})[0]
        item = json.loads(doc)
        self.assertEqual(article['headline'], item['message_subject'])

    def test_paragraphs(self):
        """Test that paragraphs (block elements) are followed by line feed in text version

        SDESK-824 regression test
        """
        article = {
            'source': 'AAP',
            'anpa_take_key': 'take',
            'subject': [{'qcode': '02011001'}],
            'format': 'HTML',
            'type': 'text',
            'body_html': '<p>paragraph 1</p><br><br><p>paragraph 2</p><p>paragraph 3</p>',
            'word_count': '1',
            'priority': 1,
            'place': [{'qcode': 'VIC', 'name': 'VIC'}],
            'genre': [],
            'sign_off': 'aa/bb'
        }
        article['versioncreated'] = datetime.datetime(year=2017, month=2, day=24, hour=16, minute=40, second=56,
                                                      tzinfo=utc)
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]

        item = json.loads(doc)
        self.assertEqual(item['message_text'], 'VIC: \nPublished At : Fri Feb 24 17:40:56 2017\n'
                                               ' take\n\n--------------------------------------'
                                               '--------------------\n\n\n\nparagraph 1\n\n\n'
                                               'paragraph 2\nparagraph 3\n\nAAP aa/bb\n')

    def test_dateline_html(self):
        """Check that message_html output is producted even without a dateline

        SDESK-836 regression test
        """
        article = {
            'format': 'HTML',
            'type': 'text',
            'body_html': '<p>some HTML</p>'}
        _, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        item = json.loads(doc)
        self.assertIsNotNone(item['message_html'])

    def test_featuremedia(self):
        article = {
            'source': 'AAP',
            'anpa_take_key': 'take',
            'subject': [{'qcode': '02011001'}],
            'format': 'HTML',
            'type': 'text',
            'body_html': '<p>Test</p>',
            'word_count': '1',
            'priority': 1,
            'place': [{'qcode': 'VIC', 'name': 'VIC'}],
            'genre': [],
            'sign_off': 'aa/bb',
            'associations': {
                'featuremedia': {
                    'archive_description': 'A woman crosses Bourke Street Mall',
                    'renditions': {
                        'viewImage': {
                            'poi': {
                                'y': 257,
                                'x': 454
                            },
                            'href': 'http://localhost:5000/api/upload-raw/5c11ece81d41c89113ed202b?_schema=http',
                            'media': '5c11ece81d41c89113ed202b',
                            'height': 390,
                            'mimetype': 'image/jpeg',
                            'width': 640
                        }
                    }
                }
            }
        }
        article['versioncreated'] = datetime.datetime(year=2017, month=2, day=24, hour=16, minute=40, second=56,
                                                      tzinfo=utc)
        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        item = json.loads(doc)
        self.assertEqual(item['renditions']['viewImage']['media'], '5c11ece81d41c89113ed202b')

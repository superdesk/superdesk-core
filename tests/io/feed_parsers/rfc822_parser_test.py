
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

import superdesk
from superdesk.io.feed_parsers.rfc822 import EMailRFC822FeedParser
from superdesk.tests import TestCase, setup
from superdesk.errors import IngestEmailError
from superdesk.users.services import UsersService


class RFC822TestCase(TestCase):
    filename = 'simple_email.txt'

    def setUp(self):
        setup(context=self)
        with self.app.app_context():
            # mock one user:
            user_service = UsersService(
                'users', backend=superdesk.get_backend())
            self.user_id = user_service.create([{
                'name': 'user',
                'user_type': 'administrator',
                'email': 'asender@a.com.au'
            }])[0]

            provider = {'name': 'Test'}
            dirname = os.path.dirname(os.path.realpath(__file__))
            fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
            with open(fixture, mode='rb') as f:
                bytes = f.read()
            parser = EMailRFC822FeedParser()
            self.items = parser.parse([(1, bytes)], provider)

    def test_headline(self):
        self.assertEqual(self.items[0]['headline'], 'Test message 1234')

    def test_body(self):
        self.assertEqual(self.items[0]['body_html'].strip(),
                         '<div dir="ltr">body text<br clear="all"/><div>&#13;\n</div></div>')

    def test_from(self):
        self.assertEqual(self.items[0]['original_source'],
                         'a sender <asender@a.com.au>')
        self.assertEqual(self.items[0]['original_creator'], self.user_id)


class RFC822ComplexTestCase(TestCase):
    filename = 'composite_email.txt'

    def setUp(self):
        setup(context=self)
        with self.app.app_context():
            provider = {'name': 'Test'}
            dirname = os.path.dirname(os.path.realpath(__file__))
            fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
            with open(fixture, mode='rb') as f:
                bytes = f.read()
            parser = EMailRFC822FeedParser()
            self.items = parser.parse([(1, bytes)], provider)

    def test_composite(self):
        self.assertEqual(len(self.items), 3)
        for item in self.items:
            self.assertIn('versioncreated', item)

    def test_from(self):
        self.assertEqual(self.items[0]['original_source'],
                         'someone <a@a.com.au>')
        self.assertNotIn('original_creator', self.items[0])


class RFC822OddCharSetTestCase(TestCase):
    filename = 'odd_charset_email.txt'

    def setUp(self):
        setup(context=self)
        with self.app.app_context():
            provider = {'name': 'Test'}
            dirname = os.path.dirname(os.path.realpath(__file__))
            fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
            with open(fixture, mode='rb') as f:
                bytes = f.read()
            parser = EMailRFC822FeedParser()
            self.items = parser.parse([(1, bytes)], provider)

    def test_headline(self):
        # This tests a subject that fails to decode but we just try a string conversion
        self.assertEqual(self.items[0]['headline'], '=?windows-1252?Q?TravTalk���s_Special_for_TAAI_convention?=')

    def test_body(self):
        self.assertRegex(self.items[0]['body_html'], '<span lang="EN-AU">')


class RFC822CharSetInSubjectTestCase(TestCase):
    filename = 'charset_in_subject_email.txt'

    def setUp(self):
        setup(context=self)
        with self.app.app_context():
            provider = {'name': 'Test'}
            dirname = os.path.dirname(os.path.realpath(__file__))
            fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
            with open(fixture, mode='rb') as f:
                bytes = f.read()
            parser = EMailRFC822FeedParser()
            self.items = parser.parse([(1, bytes)], provider)

    def test_headline(self):
        # This test a subject that has a charset that decodes correctly
        self.assertEqual(self.items[0]['headline'], 'Google Apps News March 2015')


class RFC822FormattedEmailTestCase(TestCase):

    def setUp(self):
        setup(context=self)
        with self.app.app_context():
            self.app.data.insert('users', [{
                '_id': 123,
                'name': 'user',
                'user_type': 'administrator',
                'email': 'eharvey@aap.com.au',
                'byline': 'E Harvey'
            }])
            self.app.data.insert('desks', [{'_id': 1, 'name': 'new zealand'}])
            self.app.data.insert('vocabularies', [{'_id': 'locators',
                                                  'items': [{'is_active': True,
                                                             'name': 'ADV', 'qcode': 'ADV', 'group': ''}]},
                                                  {'_id': 'priority', 'items': [{'is_active': True,
                                                                                 'name': 'Urgent', 'qcode': '3'}]}])

            self.provider = {'name': 'Test', 'config': {'formatted': True}}

    def test_parsed_values(self):
        filename = 'googleform.txt'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        with open(fixture, mode='rb') as f:
            bytes = f.read()
        parser = EMailRFC822FeedParser()

        self.items = parser.parse([(1, bytes)], self.provider)
        self.assertEqual(self.items[0]['headline'], 'TEST NZ HEADER')
        self.assertEqual(self.items[0]['task']['desk'], 1)
        self.assertEqual(self.items[0]['original_creator'], 123)
        self.assertEqual(self.items[0]['urgency'], 1)
        self.assertEqual(self.items[0]['dateline']['text'], 'AUCKLAND, May 5 AAP -')
        self.assertEqual(self.items[0]['place'][0]['qcode'], 'ADV')
        self.assertEqual(self.items[0]['flags']['marked_for_legal'], True)
        self.assertEqual(self.items[0]['priority'], 3)
        self.assertEqual(self.items[0]['byline'], 'E Harvey')

    def test_parsed_values_Email_Address(self):
        filename = 'googleform1.txt'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', filename))
        with open(fixture, mode='rb') as f:
            bytes = f.read()
        parser = EMailRFC822FeedParser()
        self.items = parser.parse([(1, bytes)], self.provider)
        self.assertEqual(self.items[0]['headline'], 'Arnold \'worried\' about maroon-clad Roar')
        self.assertEqual(self.items[0]['task']['desk'], 1)
        self.assertEqual(self.items[0]['original_creator'], 123)
        self.assertEqual(self.items[0]['urgency'], 2)
        self.assertEqual(self.items[0]['dateline']['text'], 'BRISBANE, Nov 18 AAP -')
        self.assertEqual(self.items[0]['byline'], 'E Harvey')


class RFC822JsonEmailTestCase(TestCase):
    vocab = [{'_id': 'categories', 'items': [{'is_active': True, 'name': 'Domestic Sport', 'qcode': 's'}]}]
    desk = [{'_id': 1, 'name': 'Brisbane'}]
    user = [{'_id': 1, 'email': 'mock@mail.com.au', 'byline': 'A Mock Up', 'sign_off': 'TA'}]

    def setUp(self):
        self.app.data.insert('vocabularies', self.vocab)
        self.app.data.insert('desks', self.desk)
        self.app.data.insert('users', self.user)
        with self.app.app_context():
            self.provider = {'name': 'Test', 'config': {'formatted': True}}

    def test_formatted_email_parser(self):
        filename = 'json-email.txt'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.join(dirname, '../fixtures', filename)
        with open(fixture, mode='rb') as f:
            bytes = f.read()
        parser = EMailRFC822FeedParser()
        self.items = parser.parse([(1, bytes)], self.provider)

        self.assertEqual(self.items[0]['priority'], 5)
        self.assertEqual(self.items[0]['sign_off'], 'TA')
        self.assertEqual(self.items[0]['anpa_category'], [{'qcode': 's'}])
        self.assertEqual(self.items[0]['body_html'], '<p>Lorem ipsum</p>')
        self.assertEqual(self.items[0]['abstract'], 'Abstract-2')
        self.assertEqual(self.items[0]['headline'], 'Headline-2')
        self.assertEqual(self.items[0]['original_creator'], 1)
        self.assertEqual(self.items[0]['task']['desk'], 1)
        self.assertEqual(self.items[0]['urgency'], 4)
        self.assertEqual(self.items[0]['type'], 'text')
        self.assertEqual(self.items[0]['guid'], '<001a1140cd6ecd9de8051fab814d@google.com>')
        self.assertEqual(self.items[0]['original_source'], 'mock@mail.com.au')
        self.assertEqual(self.items[0]['slugline'], 'Slugline-2')
        self.assertEqual(self.items[0]['byline'], 'A Mock Up')

    def test_bad_user(self):
        filename = 'json-email-bad-user.txt'
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.join(dirname, '../fixtures', filename)
        with open(fixture, mode='rb') as f:
            bytes = f.read()
        parser = EMailRFC822FeedParser()

        try:
            with self.assertRaises(IngestEmailError) as exc_context:
                self.items = parser.parse([(1, bytes)], self.provider)
        except Exception:
            self.fail('Expected exception type was not raised.')

        ex = exc_context.exception
        self.assertEqual(ex.code, 6001)

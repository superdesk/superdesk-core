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
from superdesk import config
from superdesk.tests import TestCase

from superdesk.etree import etree
from superdesk.io.feed_parsers.nitf import NITFFeedParser


class NITFTestCase(TestCase):

    vocab = [{'_id': 'genre', 'items': [{'name': 'Current'}]}]

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert('vocabularies', self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture) as f:
            self.nitf = f.read()
            self.item = NITFFeedParser().parse(etree.fromstring(self.nitf), provider)


class AAPTestCase(NITFTestCase):

    filename = 'aap.xml'

    def test_headline(self):
        self.assertEqual(self.item.get('headline'), "The main stories on today's 1900 ABC TV news")

    def test_slugline(self):
        self.assertEqual(self.item.get('slugline'), 'Monitor 1900 ABC News')

    def test_subjects(self):
        self.assertEqual(len(self.item.get('subject')), 4)
        self.assertIn({'qcode': '02000000', 'name': 'Justice'}, self.item.get('subject'))
        self.assertIn({'qcode': '02003000', 'name': 'Police'}, self.item.get('subject'))
        self.assertIn({'qcode': '02003001', 'name': 'law enforcement'}, self.item.get('subject'))
        self.assertIn({'qcode': '02003002', 'name': 'investigation'}, self.item.get('subject'))

    def test_guid(self):
        self.assertEqual(self.item.get('guid'), 'AAP.115314987.5417374')
        self.assertEqual(self.item.get('guid'), self.item.get('uri'))

    def test_type(self):
        self.assertEqual(self.item.get('type'), 'text')

    def test_urgency(self):
        self.assertEqual(self.item.get('urgency'), 5)

    def test_dateline(self):
        self.assertEqual(self.item.get('dateline', {}).get('located', {}).get('city'), 'Sydney')

    def test_byline(self):
        self.assertEqual(self.item.get('byline'), 'By John Doe')

    def test_abstract(self):
        self.assertEqual(self.item.get('abstract'), 'The main stories on today\'s 1900 ABC TV news')

    def test_dates(self):
        self.assertEqual(self.item.get('firstcreated').isoformat(), '2013-10-20T08:27:51+00:00')
        self.assertEqual(self.item.get('versioncreated').isoformat(), '2013-10-20T08:27:51+00:00')

    def test_content(self):
        text = "<p>   1A) More extreme weather forecast over the next few days the <br />fire situation is likely"
        self.assertIn(text, self.item.get('body_html'))
        self.assertIsInstance(self.item.get('body_html'), type(''))
        self.assertNotIn('<body.content>', self.item.get('body_html'))

    def test_pubstatus(self):
        self.assertEqual('usable', self.item.get('pubstatus'))

    def test_ingest_provider_sequence(self):
        self.assertEqual(self.item.get('ingest_provider_sequence'), '1747')

    def test_anpa_category(self):
        self.assertEqual(self.item.get('anpa_category')[0]['qcode'], 'a')

    def test_word_count(self):
        self.assertEqual(349, self.item.get('word_count'))


class APExampleTestCase(NITFTestCase):

    filename = 'ap-nitf.xml'

    def test_headline(self):
        self.assertEqual(self.item.get('headline'), 'Can trading pollution like stocks help fight climate change?')

    def test_byline(self):
        self.assertEqual(self.item.get('byline'), 'By BERNARD CONDON')

    def test_ednote(self):
        self.assertEqual(self.item.get('ednote'), 'For global distribution')

    def test_word_count(self):
        self.assertEqual(1047, self.item.get('word_count'))


class IPTCExampleTestCase(NITFTestCase):

    filename = 'nitf-fishing.xml'

    def test_headline(self):
        self.assertEqual(self.item.get('headline'), 'Weather and Tide Updates for Norfolk')

    def test_pubstatus(self):
        self.assertEqual('canceled', self.item.get('pubstatus'))

    def test_guid(self):
        self.assertEqual('iptc.321656141.b', self.item.get('guid'))

    def test_subjects(self):
        self.assertEqual(3, len(self.item.get('subject')))

    def test_place(self):
        places = self.item.get('place', [])
        self.assertEqual(1, len(places))
        self.assertEqual('Norfolk', places[0]['name'])
        self.assertEqual('US', places[0]['code'])

    def test_expiry(self):
        self.assertEqual('2012-02-26T14:30:00+00:00', self.item.get('expiry').isoformat())

    def test_keywords(self):
        self.assertIn('fishing', self.item.get('keywords'))

    def test_ednote(self):
        self.assertEqual('Today begins an expanded format of this popular column.', self.item.get('ednote'))

    def test_byline(self):
        self.assertEqual('By Alan Karben', self.item.get('byline'))

    def test_word_count(self):
        self.assertEqual(220, self.item.get('word_count'))


class PATestCase(NITFTestCase):

    filename = 'pa1.xml'

    def test_headline(self):
        self.assertEqual(self.item.get('headline'), 'PA SPORT TRIVIA (OCTOBER 14)')

    def test_pubstatus(self):
        self.assertEqual('usable', self.item.get('pubstatus'))

    def test_guid(self):
        self.assertEqual('af1f7ad5-5619-49de-84cc-2e608538c77fSSS-3-1', self.item.get('guid'))
        self.assertEqual(self.item.get('format'), 'HTML')

    def test_subjects(self):
        self.assertEqual(4, len(self.item.get('subject')))

    def test_keywords(self):
        self.assertIn('Trivia (Oct 14)', self.item.get('keywords'))

    def test_word_count(self):
        self.assertEqual(665, self.item.get('word_count'))


class PATestCase2(NITFTestCase):

    filename = 'pa2.xml'

    def test_headline(self):
        self.assertEqual(self.item.get('headline'), '1 SOCCER INT-Teams')

    def test_pubstatus(self):
        self.assertEqual('usable', self.item.get('pubstatus'))

    def test_guid(self):
        self.assertEqual('T201510140143580001T', self.item.get('guid'))
        self.assertEqual(self.item.get('format'), 'preserved')

    def test_guid(self):
        self.assertEqual(self.item.get('type'), 'text')

    def test_subjects(self):
        self.assertEqual(0, len(self.item.get('subject')))

    def test_keywords(self):
        self.assertIn('INT-Teams', self.item.get('keywords'))

    def test_word_count(self):
        self.assertEqual(58, self.item.get('word_count'))


class ParseSubjects(TestCase):
    def test_get_subjects(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<nitf><head>'
               '<tobject tobject.type="News">'
               '<tobject.property tobject.property.type="Current" />'
               '<tobject.subject tobject.subject.refnum="02003000" '
               'tobject.subject.type="Justice" tobject.subject.matter="Police" />'
               '</tobject></head></nitf>')
        subjects = NITFFeedParser().get_subjects(etree.fromstring(xml))
        self.assertEqual(len(subjects), 2)
        self.assertIn({'qcode': '02000000', 'name': 'Justice'}, subjects)
        self.assertIn({'qcode': '02003000', 'name': 'Police'}, subjects)

    def test_get_subjects_with_invalid_qcode(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<nitf><head>'
               '<tobject tobject.type="News">'
               '<tobject.property tobject.property.type="Current" />'
               '<tobject.subject tobject.subject.refnum="00000000" '
               'tobject.subject.type="Justice" tobject.subject.matter="Police" />'
               '</tobject></head></nitf>')
        subjects = NITFFeedParser().get_subjects(etree.fromstring(xml))
        self.assertEqual(len(subjects), 0)


class MappingTestCase(TestCase):

    filename = 'mapping_test.xml'
    mapping = {
        'subject': {
            'update': True,
            'key_hook': lambda item, value: item.setdefault('subject', []).extend(value)
        },
        'subject_test': {
            'callback': lambda _: ['TEST OK'],
            'key_hook': lambda item, value: item.setdefault('subject', []).extend(value)
        },
    }

    def setUp(self):
        config.NITF_MAPPING = self.mapping
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture) as f:
            self.nitf = f.read()
            self.item = NITFFeedParser().parse(etree.fromstring(self.nitf), provider)

    def test_update_and_hook(self):
        subjects = self.item.get('subject')
        # have we got both items ?
        self.assertEqual(len(subjects), 2)
        # the initial updated subject need to be here
        self.assertIn({'qcode': '02000000', 'name': 'Kriminalitet og rettsvesen'}, subjects)
        # and our key from subject_test need to be here too
        self.assertIn('TEST OK', subjects)

    def tearDown(self):
        del config.NITF_MAPPING

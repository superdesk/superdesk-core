# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from lxml import etree
from unittest import mock
from textwrap import dedent

from superdesk.tests import TestCase
from superdesk.publish.formatters.nitf_formatter import NITFFormatter
from superdesk.publish.formatters import Formatter
from superdesk.publish import init_app


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
            'body_html': '<p>test body</p><p>привет</p>',
            'type': 'text',
            'priority': '1',
            '_id': 'urn:localhost.abc',
            'urgency': 2
        }

        seq, doc = self.formatter.format(article, {'name': 'Test Subscriber'})[0]
        nitf_xml = etree.fromstring(doc)
        self.assertEqual(nitf_xml.find('head/title').text, article['headline'])
        self.assertEqual(nitf_xml.findall('body/body.content/p')[0].text, 'test body')
        self.assertEqual(nitf_xml.findall('body/body.content/p')[1].text, 'привет')
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
                    <h6>удаленный</h6>
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
                    <hl2>удаленный</hl2>
                </p>
            </div>""").replace('\n', '').replace(' ', '')
        self.assertEqual(etree.tostring(nitf, encoding='unicode').replace('\n', '').replace(' ', ''), expected)

    def test_html2nitf_br(self):
        """Check that <br/> is kept if it is a child of and enrichedText parent element"""
        html = etree.fromstring(dedent("""\
            <div>
                <br/>the previous tag should be удаленный (but not the text)
                    <p>
                        the following tag <br/> should still be here
                        and the next one <br/> too
                    </p>
            </div>
            """))

        nitf = self.formatter.html2nitf(html, attr_remove=['style'])

        expected = dedent("""\
            <div>
                the previous tag should be удаленный (but not the text)
                    <p>
                        the following tag <br/> should still be here
                        and the next one <br/> too
                    </p>
            </div>""")
        self.assertEqual(etree.tostring(nitf, encoding='unicode'), expected)

    def test_body_content_br(self):
        article = {
            "_id": "urn:newsml:localhost:2017-05-24T16:56:29.742769:3d1faf62-6f70-4b28-9222-93ec603b7af0",
            "guid": "urn:newsml:localhost:2017-05-24T16:56:29.742769:3d1faf62-6f70-4b28-9222-93ec603b7af0",
            "state": "published",
            "body_html": "<p>Sydney's Lindt Cafe siege hostages endured 17-hours of torture but, in the end, it "
                         "may have been a 10-minute delay by police that cost two lives.</p><p>Shortly after 2am "
                         "on December 16, 2014, gunman Man Haron Monis fired at escaping hostages.</p><p>That first "
                         "shot by Monis&nbsp;should have satisfied a so-called \"secondary trigger\" prompting "
                         "police to storm the Martin Place stronghold with some element of surprise, NSW Coroner "
                         "Michael Barnes found on Wednesday.</p><p>\"(But) the 10 minutes that lapsed without "
                         "decisive action by police was too long,\" Mr Barnes&nbsp;said in Sydney.</p><p>By the "
                         "time police smashed their way into the cafe at 2.14am in a flurry of stun-grenade "
                         "explosions, manager Tori Johnson had been forced to his knees and shot in the head."
                         "</p><p>Barrister Katrina Dawson was killed by police bullet fragments.</p><p>New police "
                         "commissioner Mick Fuller - who was one of the first commanders at the scene - admitted on "
                         "Wednesday tactical officers should have gone in earlier.</p><p>Mr Fuller went further than "
                         "the coroner when he told the Ten Network: \"We probably should have gone in before the "
                         "first shot.\"</p><p>\"Early intervention for terrorist incidents is the way forward, "
                         "knowing what we know now,\" he said.</p><p>\"But nevertheless it's still a very "
                         "dangerous tactic and people will potentially still lose their lives.\"</p><p>Mr Barnes "
                         "has made 45 findings on everything from police negotiation strategies to greater legal "
                         "protections for frontline officers in terrorist situations.<br></p><p>He lay the blame "
                         "for the loss of life squarely at the feet of Monis, but other parties, including prosecution "
                         "solicitors and a consulting psychiatrist, copped some criticism.</p><p>The cafe "
                         "was \"transformed into a prison run by a vicious maniac\" that day, Mr Barnes "
                         "said.<br></p><p class=\"\">The traditional \"contain and negotiate\" strategy was "
                         "appropriate early on but police failed to adequately reassess taking into account the "
                         "headway they were making with Monis.<br></p><p class=\"\">\"Sadly, it failed,\" Mr Barnes "
                         "said on Wednesday.<br></p><p class=\"\">\"The 'contain and negotiate' approach may not be "
                         "the best ongoing response to a terrorist incident if the offenders believe, whether or not "
                         "they survive, their cause will benefit from the publicity generated by a protracted "
                         "siege.\"<br></p><p class=\"\">Mr Fuller said the containment strategy had saved countless "
                         "lives over the years and wouldn't be abandoned for non-terrorist incidents.</p>"
                         "<p class=\"\">Police mistakenly thought Monis' backpack could house explosives, "
                         "but Mr Barnes noted senior officers were \"unduly reluctant\" to initiate direct action "
                         "plans during siege situations.</p><p class=\"\">The \"primary trigger\" for such an "
                         "assault was identified as the death or serious injury of a hostage - evidence which "
                         "disgusted the families of victims and survivors.</p><p class=\"\">The police response was "
                         "at times hampered by mishaps.</p><p>Eight calls to a phone number hostages expected would "
                         "connect them with negotiators were missed, which was a \"significant failure\", Mr Barnes "
                         "said.</p><p>Commanders and tactical officers received specialist terrorist training but "
                         "negotiators received \"little, if any\", the coroner added.</p><p>The stand-off could not "
                         "have eventuated in the first place if Monis had not been granted bail on accessory to murder"
                         " and dozens of sexual assault offences.<br></p><p>Mr Barnes found the work of an Office of "
                         "the Director of Public Prosecutions solicitor in December 2013 was inadequate, "
                         "\"erroneously\" advising a court Monis didn't have to show exceptional circumstances "
                         "in arguing for bail.</p><p>Police also made a mistake by issuing Monis with a court "
                         "attendance notice for the sexual offences in October 2014 rather than arresting him"
                         ".</p><p>Monis was already on bail at the time for a commonwealth offence after he'd "
                         "written offensive letters to the families of Australian soldiers killed in the Middle"
                         " East.</p><p>States can find it difficult to access commonwealth records, Mr Barnes said,"
                         " and he called for that to be remedied.</p><p>Some of the coroner's harshest individual "
                         "criticism was reserved for the consultant psychiatrist who advised police.</p>"
                         "<p>His \"sub-optimal\" performance included a belief that Monis was merely grandstanding,"
                         " Mr Barnes found.</p><p>The doctor should not have been permitted to advise on negotiation "
                         "strategy and he made \"erroneous and unrealistic assessments\" of what was happening inside "
                         "the cafe.</p><p>The psychiatrist's advice was ambiguous and Islamic terrorism was beyond his"
                         " expertise.</p><p>\"The police commanders underestimated the threat Monis posed,\" Mr Barnes"
                         " said, in part blaming their reliance upon the psychiatrist's opinion.</p><p>He recommended "
                         "a more diverse panel of experts be used in the future.</p><p>The coroner stated police "
                         "snipers couldn't have ended the siege despite a 10-minute window where they had clear sight "
                         "of a head that could have been Monis.</p><p>Those gunmen were never confident in their legal "
                         "justification for a \"kill shot\" and Mr Barnes suggested their&nbsp;power to use force "
                         "should be more clearly defined.</p><p>The coroner did acknowledge that sending tactical "
                         "officers into the cafe after their hand was forced was a decision no commander would "
                         "ever want to face.</p><p>\"The bravery of these officers inspires awe,\" he said.<br></p>",
            "pubstatus": "usable",
            "type": "text",
            "abstract": "<p>The NSW coroner believes a 10-minute period of inaction by police before the bloody end "
                        "of the 2014 Lindt Cafe siege was \"too long\".</p>",
            "priority": 6,
            "unique_id": 12055427,
            "format": "HTML",
            "genre": [
                {
                    "qcode": "Wrap",
                    "name": "Wrap"
                }
            ],
            "word_count": 843,
            "source": "AAP",
            "urgency": 1,
            "subject": [
                {
                    "qcode": "16001000",
                    "parent": "16000000",
                    "name": "act of terror"
                },
                {
                    "qcode": "02001010",
                    "parent": "02001000",
                    "name": "terrorism"
                }
            ],
            "flags": {
                "marked_archived_only": False,
                "marked_for_legal": False,
                "marked_for_not_publication": False,
                "marked_for_sms": False
            },
            "headline": "'Ten minutes was too long': Lindt siege",
            "dateline": {
                "source": "AAP",
                "text": "SYDNEY, May 24 AAP -",
                "located": {
                    "city": "Sydney",
                    "country_code": "AU",
                    "country": "Australia",
                    "dateline": "city",
                    "state_code": "NSW",
                    "state": "New South Wales",
                    "alt_name": "",
                    "tz": "Australia/Sydney",
                    "city_code": "Sydney"
                }
            },
            "anpa_category": [
                {
                    "qcode": "a",
                    "name": "Australian General News"
                }
            ],
            "unique_name": "#12055427",
            "place": [
                {
                    "name": "NSW",
                    "qcode": "NSW",
                    "country": "Australia",
                    "world_region": "Oceania",
                    "group": "Australia",
                    "state": "New South Wales"
                }
            ],
            "sign_off": "SN/jmk/jcd/pmu",
            "anpa_take_key": "2nd Wrap (pix/video available)",
            "language": "en",
            "slugline": "Cafe",
            "byline": "Jamie McKinnell",
            "version": 2,
        }

        response = self.formatter.format(article, {})
        nitf_xml = etree.fromstring(response[0][1])
        self.assertEqual(etree.tostring(nitf_xml.find('body/body.content/p'), encoding="unicode"),
                         "<p>Sydney's Lindt Cafe siege hostages endured 17-hours of torture but, in the end, it may "
                         "have been a 10-minute delay by police that cost two lives.</p>\n      ")
        self.assertTrue(nitf_xml.findall('body/body.content/p')[1].text.startswith('Shortly after 2am'))

    def test_html2nitf_br_last(self):
        """Check that last <br/> in a <p> element is removed"""
        html = etree.fromstring(dedent("""\
            <div>
                    <p>
                        the following tag <br/> should still be here
                    </p>
                    <p>
                        and the next one <br/> too
                    </p>
                    <p>
                        but not the last one:<br/>
                    </p>
            </div>
            """))

        nitf = self.formatter.html2nitf(html, attr_remove=['style'])

        expected = dedent("""\
            <div>
                    <p>
                        the following tag <br/> should still be here
                    </p>
                    <p>
                        and the next one <br/> too
                    </p>
                    <p>
                        but not the last one:
                    </p>
            </div>""")
        self.assertEqual(etree.tostring(nitf, encoding='unicode'), expected)

    def test_html2nitf_style_cleaning(self):
        """Check that <style> element and style attribute are removed from HTML"""
        html = etree.fromstring(dedent("""\
            <div>
                <style type="text/css">
                    p { margin-bottom: 0.25cm; line-height: 120%; }a:link {  }
                </style>
                <p style="margin-bottom: 0cm; line-height: 100%">Test bla bla bla</p>
                <p style="margin-bottom: 0cm; line-height: 100%">
                    <br/>
                </p>
                <p style="margin-bottom: 0cm; line-height: 100%">
                    <font face="DejaVu Sans, sans-serif">
                        <font style="font-size: 14pt" size="4">
                            <i>
                                <u>
                                    <b>test</b>
                                </u>
                            </i>
                        </font>
                    </font>
                </p>
                <p style="margin-bottom: 0cm; line-height: 100%">toto</p>
                <p style="margin-bottom: 0cm; line-height: 100%">titi</p>
            </div>
            """))

        nitf = self.formatter.html2nitf(html, attr_remove=['style'])

        expected = dedent("""\
            <div>
                <p>Test bla bla bla</p>
                <p>
                </p>
                <p>
                    <em class="italic">
                        <em class="underscore">
                            <em class="bold">test</em>
                        </em>
                    </em>
                </p>
                <p>toto</p>
                <p>titi</p>
            </div>""").replace('\n', '').replace(' ', '')
        self.assertEqual(etree.tostring(nitf, encoding='unicode').replace('\n', '').replace(' ', ''), expected)

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
        self.assertEqual(etree.tostring(nitf, encoding='unicode'), html_raw)

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
            'body_html': '<p>Томми Mäkinen crashes a Škoda in Äppelbo</p>',
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
        self.assertEqual(nitf_xml.find('body/body.content/p').text, 'Томми Mäkinen crashes a Škoda in Äppelbo')

    def test_null_genre(self):
        article = {
            '_id': '3',
            'source': 'AAP',
            'genre': None,
            'anpa_category': [{'qcode': 'a'}],
            'headline': 'This is a test headline',
            'byline': 'joe',
            'slugline': 'slugline',
            'subject': [{'qcode': '02011001'}],
            'anpa_take_key': 'take_key',
            'unique_id': '1',
            'type': 'text',
            'body_html': '<p>Томми Mäkinen crashes a Škoda in Äppelbo</p>',
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
        self.assertIsNotNone(doc)

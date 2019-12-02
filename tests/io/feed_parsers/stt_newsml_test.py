# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.io.feed_parsers.stt_newsml import STTNewsMLFeedParser
from superdesk.tests import TestCase
from lxml import etree
import os


class BaseSTTNewsMLTestCase(TestCase):
    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../fixtures', self.filename))
        provider = {'name': 'Test'}
        with open(fixture, 'rb') as f:
            parser = STTNewsMLFeedParser()
            self.xml_root = etree.parse(f).getroot()
            self.item = parser.parse(self.xml_root, provider)


class STTTestCase(BaseSTTNewsMLTestCase):
    filename = 'stt_newsml_test.xml'

    def test_can_parse(self):
        self.assertTrue(STTNewsMLFeedParser().can_parse(self.xml_root))

    def test_content(self):
        item = self.item[0]
        self.assertEqual(
            item['headline'],
            'Parliament passed the Alcohol Act and the government gained confidence' '*** TRANSLATED ***',
        )
        self.assertEqual(item['guid'], 'urn:newsml:stt.fi:20171219:101801633:4')
        self.assertEqual(item['uri'], 'urn:newsml:stt.fi:20171219:101801633')
        self.assertEqual(item['firstcreated'].isoformat(), '2017-12-19T10:33:04+02:00')
        expected_body = (
            '<p>*** DISCLAIMER: THIS IS AN AUTOMATED TRANSLATION FROM FINNISH ***</p>\n\n<h2>Also the une'
            'mployment law went through</h2>\n\n<p>The Parliament has approved the Alcohol Act 124-65. Th'
            'ere were two absentee voices and eight MPs absent. As early as Friday, Parliament voted for '
            'the percentage of alcohol in the grocery store to rise to 5.5.</p>\n\n<p>Government parties '
            'have previously agreed that the tax on alcohol will be tightened by EUR 100 million, as the '
            'maximum percentage of alcoholic beverages sold in the store will increase.</p>\n\n<p>In addi'
            'tion to the alcohol percentage, the Alcohol Act includes a significant number of reforms. Wi'
            'th the new Alcohol Act, the restaurant can, for example, continue to dispense with a notice '
            'until 4 o&amp;#39;clock. The restaurant may be open after one hour of serving.</p>\n\n<p>In '
            'the future, food stores may also sell non-fermented alcoholic beverages, so-called limousine'
            's. The creatures can be open on weekdays for an hour longer, or at night.</p>\n\n<p>Parliame'
            'nt also approved the proposal by Hannakaisa Heikkinen (central) that the government should c'
            'larify the rules on distance selling of alcohol. The distance selling was left unclear in th'
            'e bill and in the report on it. The family and basic minister Annika Saarikko (center) has a'
            'lready announced that she will set up a distance marketing team to investigate.</p>\n\n<p>&a'
            'mp;quot;The will of the government is that we do not want to break Alko&amp;#39;s monopoly w'
            'ith any of the risk factors that distance selling could include. If the sales of spirits in '
            'Finland are limitedAlkoon, the same applies to foreign journalists, Saarikko said on Friday.'
            '</p>\n\n<p>Distance selling means the purchase of alcohol from another EU Member State so th'
            'at the seller is responsible for the transport of drinks or the organization of transport to'
            ' the purchaser.</p>\n\n<p>Parliament also voted on the government&amp;#39;s confidence. The '
            'government gained confidence by 106-80. Seven MPs were absent and six were absent.</p>\n\n<p'
            '></p>\n<p>\n</p>\n<h3>Rinne: Hallitus runnoi läpi työttömiä kurittavan lain</h3>\n\n\n<p></p'
            '>\n\n<p>In the morning&amp;#39;s vote, for example, a controversial unemployed security law '
            'passed through 103-90. There were two absentee voices and four MPs absent.</p>\n\n<p>The opp'
            'osition has strongly opposed, in particular, the law-related active model, according to whic'
            'h 4.65 percent of the unemployment allowance is reduced if the unemployed person does not qu'
            'alify for an adequate amount of paid employment or participates in employment promotion serv'
            'ices over a period of three months.</p>\n\n<p>- The government parties are running the unemp'
            'loyed through a law to cure, despite warnings. We do not accept that the unemployed are puni'
            'shed for the fact that there is simply no job. That is why the SDP will change the active mo'
            'del, Rinne said in a briefing after the vote.</p>\n\n<p></p>\n<p>*** DISCLAIMER: DETTA ÄR EN'
            ' AUTOMATISK ÖVERSÄTTNING FRÅN FINNISH ***</p>\n<p>Parlamentet har godkänt alkohollagen 124-6'
            '5. Det fanns två frånvarande röster och åtta ledamöter frånvarande. Redan i fredags röstade '
            'parlamentet för att andelen alkohol i livsmedelsbutiken skulle stiga till 5,5.</p>\n<p>Reger'
            'ingspartierna har tidigare kommit överens om att alkoholskatten kommer att stramas med 100 m'
            'iljoner euro, eftersom den högsta andelen alkoholhaltiga drycker som säljs i affären kommer '
            'att öka.</p>\n<p>Förutom alkoholprocenten innehåller alkohollagen ett betydande antal reform'
            'er. Med den nya alkohollagen kan restaurangen till exempel fortsätta att meddela ett meddela'
            'nde till klockan 4. Restaurangen kan vara öppen efter en timmes servering.</p>\n<p>I framtid'
            'en kan mataffärer också sälja alkoholfria drycker, så kallade limousiner. Varelserna kan var'
            'a öppna på vardagar för en timme längre eller på natten.</p>\n<p>Parlamentet godkände också '
            'förslaget från Hannakaisa Heikkinen (central) att regeringen skulle klargöra reglerna för di'
            'stansförsäljning av alkohol. Distansförsäljningen lämnades oklart i propositionen och rappor'
            'ten om den. Familjen och grundminister Annika Saarikko (center) har redan meddelat att hon k'
            'ommer att inrätta ett distansmarknadsföringslag att undersöka.</p>\n<p>&amp;quot;Regeringens'
            ' vilja är att vi inte vill bryta Alkos monopol med någon av de riskfaktorer som distansförsä'
            'ljningen kan innefatta. Om försäljningen av sprit i Finland är begränsad</p>\n<p>, detsamma '
            'gäller utländska journalister, sa Saarikko på fredag.</p>\n<p>Distansförsäljning innebär ink'
            'öp av alkohol från en annan EU-medlemsstat så att säljaren är ansvarig för transport av dryc'
            'ker eller transporten till köparen.</p>\n<p>Parlamentet röstade också om regeringens förtroe'
            'nde. Regeringen fick förtroende med 106-80. Sju parlamentsledamöter var frånvarande och sex '
            'var frånvarande.</p>\n<p></p>\n<p></p>\n<p>På morgonens omröstning gick exempelvis en kontro'
            'versiell arbetslös säkerhetslag genom 103-90. Det fanns två frånvarande röster och fyra leda'
            'möter frånvarande.</p>\n<p>Oppositionen har starkt motsatt sig, i synnerhet den lagrelaterad'
            'e aktiva modellen, enligt vilken 4,65 procent av arbetslöshetsersättningen minskas om den ar'
            'betslösa inte kvalificerar sig för tillräcklig betald anställning eller deltar i arbetsförme'
            'dlingstjänster under en period på tre månader.</p>\n<p>- Regeringspartierna driver de arbets'
            'lösa genom en lag att bota, trots varningar. Vi accepterar inte att de arbetslösa straffas f'
            'ör att det bara inte finns något jobb. Det är därför som SDP kommer att ändra den aktiva mod'
            'ellen, sade Rinne i en briefing efter omröstningen.</p>\n<p>*** DISCLAIMER: THIS IS AN AUTOM'
            'ATED TRANSLATION FROM FINNISH ***</p>\n<p>Eduskunta on hyväksynyt alkoholilain äänin 124–65.'
            ' Tyhjää äänesti kaksi ja poissa oli kahdeksan kansanedustajaa. Jo perjantaina eduskunta ääne'
            'sti, että ruokakaupassa myytävän alkoholin prosenttiraja nousee 5,5:een. </p>\n<p> Hallitusp'
            'uolueet ovat aiemmin sopineet, että alkoholiveroa kiristetään 100 miljoonalla eurolla, kun k'
            'aupassa myytävien alkoholijuomien enimmäisprosentti nousee.</p>\n<p>Alkoholilakiin sisältyy '
            'alkoholiprosentin lisäksi merkittävä määrä uudistuksia. Uuden alkoholilain myötä ravintola v'
            'oi esimerkiksi jatkaa anniskelua pelkällä ilmoituksella kello neljään saakka. Ravintola voi '
            'olla auki tunnin anniskelun päättymisen jälkeen.</p>\n<p>Jatkossa ruokakaupassa saa myydä my'
            'ös muutoin kuin käymisteitse valmistettuja alkoholijuomia eli niin sanottuja limuviinoja. Al'
            'kot saavat olla arkisin auki tunnin pidempään eli iltayhdeksään.</p>\n<p>Eduskunta hyväksyi '
            'lisäksi Hannakaisa Heikkisen (kesk.) lausumaehdotuksen, jonka mukaan hallituksen on selvitet'
            'tävä alkoholin etämyyntiä koskevat säännökset. Etämyynti jäi lakiesityksessä ja sitä koskeva'
            'ssa mietinnössä epäselväksi. Perhe- ja peruspalveluministeri Annika Saarikko (kesk.) on jo k'
            'ertonut asettavansa työryhmän etämyyntiä selvittämään.</p>\n<p>– Hallituksen tahdonilmaus on'
            ', että emme halua murtaa Alkon monopolia millään riskitekijöillä, joita etämyynti voisi pitä'
            'ä sisällään. Jos Suomessa väkevien alkoholijuomien myynti on rajoitettu </p>\n<p>, sama kosk'
            'ee myös ulkomaisia toimittajia, Saarikko sanoi perjantaina.</p>\n<p>Etämyynti tarkoittaa alk'
            'oholin hankintaa toisesta EU:n jäsenvaltiosta siten, että myyjä vastaa juomien kuljetuksesta'
            ' tai kuljetuksen järjestämisestä ostajalle.</p>\n<p>Eduskunta äänesti myös hallituksen luott'
            'amuksesta. Hallitus sai luottamuksen äänin 106–80. Tyhjää äänesti seitsemän kansanedustajaa '
            'ja poissa oli kuusi.</p>\n<p>\n</p>\n<p>\n</p>\n<p>Aamupäivän äänestyksissä meni läpi myös e'
            'simerkiksi kiistelty työttömyysturvalaki äänin 103–90. Tyhjää äänesti kaksi ja poissa oli ne'
            'ljä kansanedustajaa. </p>\n<p>Oppositio on vastustanut jyrkästi etenkin lakiin liittyvää akt'
            'iivimallia, jonka mukaan työttömyyskorvauksesta nipistetään 4,65 prosenttia, jos työtön ei k'
            'äy riittävää määrää palkkatyössä tai osallistu työllistymistä edistäviin palveluihin kolmen '
            'kuukauden aikana.</p>\n<p>–\u2009 Hallituspuolueet runnoivat työttömiä kurittavan lain läpi '
            'varoituksista huolimatta. Me emme hyväksy sitä, että työttömiä rangaistaan siitä, että työtä'
            ' ei yksinkertaisesti ole. Siksi SDP tulee muuttamaan aktiivimallin, Rinne sanoi tiedotteessa'
            'an heti äänestyksen jälkeen.</p>'
        )

        self.assertEqual(item['body_html'], expected_body)

    def test_department_version(self):
        """Test that subject is parsed correctly (STTNHUB-18)"""
        item = self.item[0]
        self.assertEqual(item['subject'], [{'qcode': '9', 'name': 'Politics', 'scheme': 'sttdepartment'},
                                           {'qcode': '4', 'name': 'Pika+', 'scheme': 'sttversion'}])

    def test_genre_version(self):
        """Test that genre and version are parsed correctly (STTNHUB-18)"""
        item = self.item[0]
        self.assertEqual(item['genre'], [{'qcode': '1', 'name': 'Pääjuttu'}])


class STTLocationTestCase(BaseSTTNewsMLTestCase):
    """Test location metadata"""

    filename = 'stt_newsml_location_test.xml'

    def test_location(self):
        """Test that STT location metadata are parsed correctly (STTNHUB-18)"""
        item = self.item[0]
        expected = [
            {'qcode': '7576',
             'scheme': 'sttlocmeta',
             'locality_code': '392',
             'locality': 'Tallinna',
             'state_code': '67',
             'state': 'N/A',
             'country': 'Viro',
             'country_code': '238',
             'world_region_code': '150',
             'world_region': 'Eurooppa'},
            {'qcode': '8975',
             'scheme': 'sttlocmeta',
             'country': 'Suomi',
             'country_code': '1',
             'world_region_code': '150',
             'world_region': 'Eurooppa'}]

        self.assertEqual(item['place'], expected)


class STTRichLocationTestCase(BaseSTTNewsMLTestCase):

    filename = 'stt_newsml_location_rich.xml'

    def test_location(self):
        item = self.item[0]
        self.assertIn({
            'qcode': '20016',
            'scheme': 'sttlocmeta',
            'name': 'Myanmar',
            'world_region': 'Aasia',
            'world_region_code': '142',
        }, item['place'])


class STTNoHLTestCase(BaseSTTNewsMLTestCase):
    """Test case with a source without headline"""

    filename = 'stt_newsml_test_no_hl.xml'

    def test_default_headline(self):
        """Test that body is used when there is no headline set"""
        item = self.item[0]
        self.assertEqual(
            item['headline'],
            '*** DISCLAIMER: THIS IS AN AUTOMATED TRANSLATION FROM FINNISH ***' '\n\nAlso the unemployment law went th',
        )


class STTAbstractTestCase(BaseSTTNewsMLTestCase):
    filename = 'stt_newsml_abstract_test.xml'

    def test_content(self):
        item = self.item[0]
        self.assertEqual(
            item['abstract'],
            'Hjallis Harkimo ja Mikael Jungner ovat perustamassa uutta poliittista '
            'liikettä perinteisiä puolueita haastamaan, uutisoi Helsingin Sanomat.',
        )

    def test_subject(self):
        item = self.item[0]
        self.assertEqual(
            item['subject'],
            [
                {'qcode': '9', 'name': 'Politiikka', 'scheme': 'sttdepartment'},
                {'qcode': '11000000', 'scheme': 'sttsubj', 'name': 'Politiikka'},
                {'qcode': '11009000', 'scheme': 'sttsubj', 'name': 'Eduskunta Parlamentti'},
                {'qcode': '11000000', 'scheme': 'sttsubj', 'name': 'Politiikka'},
                {'qcode': '11010000', 'scheme': 'sttsubj', 'name': 'Puolueet Yhteiskunnalliset liikkeet '},
                {'qcode': '11010999', 'scheme': 'sttsubj', 'name': 'Muut puolueet ja poliittiset ryhmät'},
                {'qcode': '11000000', 'scheme': 'sttsubj', 'name': 'Politiikka'},
                {'qcode': '11010000', 'scheme': 'sttsubj', 'name': 'Puolueet Yhteiskunnalliset liikkeet '},
                {'qcode': '11010992', 'scheme': 'sttsubj', 'name': 'Kokoomus'},
                {'name': 'Viiva', 'qcode': '1', 'scheme': 'sttversion'}
            ],
        )


class STTNoteTestCase(BaseSTTNewsMLTestCase):
    filename = 'stt_newsml_note_test.xml'

    def test_notes(self):
        """Check that notes are parsed correctly (STTNHUB-18)"""
        item = self.item[0]
        self.assertEqual(
            item['ednote'],
            'Korjattu aiempaa uutista: Ylen juttu perustuu Puolustusvoimissa merkittävässä asemassa olevaan lähteeseen,'
            ' ei puolustusministeriössä kuten aiemmin kerroimme.'
        )
        self.assertEqual(
            item['extra']['sttnote_private'],
            '2. väliotsikon jälkeen 2. kpl. puolustusministeriössä po. Puolustusvoimissa'
        )

    def test_byline(self):
        item = self.item[0]
        self.assertEqual(item['byline'], 'ANTTI AUTIO, HETA HASSINEN ')


class STTArchiveTestCase(BaseSTTNewsMLTestCase):
    filename = 'stt_archive_newsml_test.xml'

    def test_timestamps(self):
        item = self.item[0]
        self.assertEqual('2013-02-16T15:36:20+00:00', item['firstcreated'].isoformat())
        self.assertEqual('2013-02-22T16:36:20+00:00', item['versioncreated'].isoformat())
        self.assertEqual('2013-02-22T16:36:20+00:00', item['firstpublished'].isoformat())

        self.assertIn({'qcode': '5', 'scheme': 'sttdone1', 'name': ''}, item['subject'])

        # test daylight savings
        self.assertEqual('2018-01-01T10:00:00+00:00', STTNewsMLFeedParser().datetime('2018-01-01T12:00:00').isoformat())
        self.assertEqual('2018-08-01T09:00:00+00:00', STTNewsMLFeedParser().datetime('2018-08-01T12:00:00').isoformat())

    def test_source(self):
        item = self.item[0]
        self.assertEqual('STT', item['source'])


class STTArchiveCreatedDateTestCase(BaseSTTNewsMLTestCase):
    """Tests versionCreated date has the value of contentCreated when there is no contentUpdated date"""

    filename = 'stt_archive_newsml_created_date_test.xml'

    def test_timestamps(self):
        item = self.item[0]
        self.assertEqual('2013-02-16T15:36:20+00:00', item['firstcreated'].isoformat())
        self.assertEqual('2013-02-16T15:36:20+00:00', item['versioncreated'].isoformat())
        self.assertEqual('2013-02-16T15:36:20+00:00', item['firstpublished'].isoformat())


class STTEndashTestCase(BaseSTTNewsMLTestCase):
    filename = 'stt_newsml_endash.xml'

    def test_can_parse(self):
        self.assertTrue(STTNewsMLFeedParser().can_parse(self.xml_root))

    def test_content(self):
        item = self.item[0]
        self.assertNotIn('endash', item['body_html'])
        self.assertIn('35-40', item['body_html'])

    def test_source(self):
        item = self.item[0]
        self.assertEqual('STT-Sourcefabric', item['source'])


class STTSubjectTestCase(BaseSTTNewsMLTestCase):
    filename = 'stt_newsml_subject_test.xml'

    def test_can_parse(self):
        self.assertTrue(STTNewsMLFeedParser().can_parse(self.xml_root))

    def test_subject(self):
        item = self.item[0]
        self.assertIn({
            'qcode': '11006000',
            'scheme': 'sttsubj',
            'name': 'Julkinen hallinto',
        }, item['subject'])
        self.assertIn({
            'qcode': '11006006',
            'name': 'heads of state',
        }, item['subject'])

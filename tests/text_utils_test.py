import unittest
from superdesk import text_utils


class WordCountTestCase(unittest.TestCase):
    def test_word_count_whitespace_string(self):
        self.assertEqual(0, text_utils.get_word_count("   "))

    def test_word_count_p_tags(self):
        self.assertEqual(2, text_utils.get_word_count("<p>foo<strong>s</strong></p><p>bar</p>"))
        self.assertEqual(500, text_utils.get_word_count("<p>word</p>" * 500))

    def test_word_count_brs(self):
        self.assertEqual(2, text_utils.get_word_count("<p>foo<br><br>bar</p>"))
        self.assertEqual(2, text_utils.get_word_count("<p>foo<br /><br />bar</p>"))

    def test_word_count_hrs(self):
        self.assertEqual(2, text_utils.get_word_count("<p>foo<br><hr>bar</p>"))
        self.assertEqual(2, text_utils.get_word_count("<p>foo<br /><hr />bar</p>"))

    def test_word_count_ul(self):
        self.assertEqual(
            3,
            text_utils.get_word_count(
                """
            <ul>
                <li>foo</li>
                <li>bar</li>
                <li>baz</li>
                <li></li>
            </ul>
        """
            ),
        )

    def test_word_count_nitf(self):
        self.assertEqual(
            37,
            text_utils.get_word_count(
                """
        <p>2014: Northern Ireland beat <location>Greece</location> 2-0 in <location>Athens</location>
        with goals from <person>Jamie Ward</person> and <person>Kyle Lafferty</person> to boost their
        hopes of qualifying for <money>Euro 2016</money>. <person>Michael O'Neill's</person> side
        sealed their place at the finals in <chron>October 2015</chron>.</p>"""
            ),
        )

    def test_word_count_nitf_2(self):
        self.assertEqual(
            314,
            text_utils.get_word_count(
                """
        <p>Rio Tinto has kept intact its target for iron ore shipments in 2017 after hitting the mid-point
        of its revised guidance range for 2016. </p><p>The world's second largest iron ore exporter shipped
        327.6 million tonnes of iron ore from its Pilbara operations in 2016, in line with the slightly lowered
        full-year guidance of between 325 and 330 million tonnes.</p><p>It expects to ship between 330 to 340
        million tonnes in 2017 from its main mining hub in WA.</p><p>"We have delivered a strong operational
        performance in 2016, underpinned by our drive for efficiency and maximising cash flow," chief executive
        Jean Sebastien Jacques said in a statement.</p><p>"Our disciplined approach remains in place in 2017,
        with the continued focus on productivity, cost reduction and commercial excellence."</p><p>Rio shipped
        87.7 million tonnes of iron ore in the December quarter - up eight per cent from the preceding three
        months - mainly helped by minimal weather disruption.</p><p>Fourth-quarter production was also up four
        per cent from a year ago to 85.5 million tonnes.</p><p>Sales in the quarter exceeded production by 2.2
        million tonnes, primarily through a drawdown on inventories built at the ports in the third quarter,
        the company said.</p><p>The miner also looks to have capitalised on a strong rebound in iron ore prices
        in 2016, saying 80 per cent of its sales were either on the spot market or on current quarter or current
        month average.</p><p>Rio’s copper production rose four per cent from a year ago to 523,000 tonnes, but
        still came in below its guidance range of 535,000 to 565,000 tonnes due to lower-than-expected production
        at its Kennecott mine in the US and no supplies from the Grasberg joint venture in Indonesia.</p><p>It has
        forecast a wide guidance range of 525,000 to 665,000 tonnes for 2017.</p><p>The miner topped production
        forecasts for bauxite and coking coal, while aluminium output jumped 10 per cent in 2016.</p>"""
            ),
        )

    def test_word_count_html(self):
        # If you change the following text, please change it in client too at
        # superdesk-client-core/scripts/apps/authoring/authoring/tests/WordCount.spec.js
        text = """
        <p>This is a test text with numbers (1 000 000 and 1,000,000 and 1.000.000)
        and <strong>compound word (two-done)</strong> and <em>abbreviation (Washington D.C.)</p>
        <p>it should be the same word count as in client and backend</p>"""
        self.assertEqual(32, text_utils.get_word_count(text))

    def test_decode(self):
        """Test decoding with encoding detection"""
        bytes_str = "téstôù".encode("latin-1")
        decoded = text_utils.decode(bytes_str)
        self.assertEqual(decoded, "téstôù")

    def test_get_par_count(self):
        self.assertEqual(
            3,
            text_utils.get_par_count(
                """
        <p>First paragraph</p>
        <p>Second paragraph</p>
        <p>Last paragraph</p>
        """
            ),
        )

        self.assertEqual(
            3,
            text_utils.get_par_count(
                """
        <p><br></p>
        <p>First paragraph</p>
        <p>Second paragraph</p>
        <p></p>
        <p>Last paragraph</p>
        <p>

        </p>
        """
            ),
        )

        self.assertEqual(
            0,
            text_utils.get_par_count(
                """
        <p>

        </p>
        """
            ),
        )

        self.assertEqual(
            0,
            text_utils.get_par_count(
                """
        <div></div>
        """
            ),
        )

        self.assertEqual(0, text_utils.get_par_count(None))

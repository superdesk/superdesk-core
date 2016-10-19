
import unittest
from superdesk.etree import get_word_count


class WordCountTestCase(unittest.TestCase):

    def test_word_count_p_tags(self):
        self.assertEqual(2, get_word_count('<p>foo<strong>s</strong></p><p>bar</p>'))

    def test_word_count_brs(self):
        self.assertEqual(2, get_word_count('<p>foo<br><br>bar</p>'))
        self.assertEqual(2, get_word_count('<p>foo<br /><br />bar</p>'))

    def test_word_count_hrs(self):
        self.assertEqual(2, get_word_count('<p>foo<br><hr>bar</p>'))
        self.assertEqual(2, get_word_count('<p>foo<br /><hr />bar</p>'))

    def test_word_count_ul(self):
        self.assertEqual(3, get_word_count("""
            <ul>
                <li>foo</li>
                <li>bar</li>
                <li>baz</li>
                <li></li>
            </ul>
        """))

    def test_word_count_nitf(self):
        self.assertEqual(37, get_word_count("""
        <p>2014: Northern Ireland beat <location>Greece</location> 2-0 in <location>Athens</location>
        with goals from <person>Jamie Ward</person> and <person>Kyle Lafferty</person> to boost their
        hopes of qualifying for <money>Euro 2016</money>. <person>Michael O'Neill's</person> side
        sealed their place at the finals in <chron>October 2015</chron>.</p>"""))

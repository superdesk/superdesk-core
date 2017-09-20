
import unittest
from superdesk import etree as sd_etree


class ParseHtmlTestCase(unittest.TestCase):
    def test_encode_carriage_return(self):
        text = 'This is first line.\r\nThis is second line.\r\n'
        parsed = sd_etree.parse_html(text)
        self.assertEqual(text.replace('\r', '&#13;'), sd_etree.to_string(parsed))

        text = '<pre>This is first line.\r\nThis is second line.\r\n</pre>'
        parsed = sd_etree.parse_html(text, content='html')
        self.assertEqual(text.replace('\r', '&#13;'), sd_etree.to_string(parsed))

    def test_void_elements_fix(self):
        html = '<p>this is a test with empty <h3/> non-void <em/> elements and a void <br/> one</p>'
        expected = '<p>this is a test with empty <h3></h3> non-void <em></em> elements and a void <br/> one</p>'
        parsed = sd_etree.parse_html(html)
        sd_etree.fix_html_void_elements(parsed)
        self.assertEqual(sd_etree.to_string(parsed), expected)

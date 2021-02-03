from superdesk import etree as sd_etree
from superdesk.tests import TestCase
from lxml import etree, html
from textwrap import dedent


class ParseHtmlTestCase(TestCase):
    def test_encode_carriage_return(self):
        text = "This is first line.\r\nThis is second line.\r\n"
        parsed = sd_etree.parse_html(text)
        self.assertEqual(text.replace("\r", "&#13;"), sd_etree.to_string(parsed))

        text = "<pre>This is first line.\r\nThis is second line.\r\n</pre>"
        parsed = sd_etree.parse_html(text, content="html")
        self.assertEqual(text.replace("\r", "&#13;"), sd_etree.to_string(parsed))

    def test_void_elements_fix(self):
        html_raw = "<p>this is a test with empty <h3/> non-void <em/> elements and a void <br/> one</p>"
        expected = "<p>this is a test with empty <h3></h3> non-void <em></em> elements and a void <br/> one</p>"
        parsed = sd_etree.parse_html(html_raw)
        sd_etree.fix_html_void_elements(parsed)
        self.assertEqual(sd_etree.to_string(parsed), expected)

    def test_clean_html(self):
        html_raw = dedent(
            """\
        <div>
           <header>this header must be removed</header>
           <p class="class_to_remove">
               <unknown_tag>bla
                   <strong>keep it strong</strong>
               </unknown_tag>
               <script>no script here !</script>
           </p>
        </div>
        """
        )
        elem = html.fromstring(html_raw)
        elem = sd_etree.clean_html(elem)
        expected = dedent(
            """\
        <div>
           this header must be removed
           <p>
               bla
                   <strong>keep it strong</strong>


           </p>
        </div>
        """
        )
        self.assertEqual(dedent(etree.tostring(elem, encoding="unicode")), expected)


from lxml import etree
from .newsml_g2_formatter import NewsMLG2Formatter


class HTMLNewsMLG2Formatter(NewsMLG2Formatter):

    def _format_content(self, article, news_item, nitf):
        """Adds the content set to the xml.

        It outputs content as html doc instead of default nitf.

        :param dict article:
        :param Element newsItem:
        :param Element nitf:
        """
        content_set = etree.SubElement(news_item, 'contentSet')
        inline = etree.SubElement(content_set, 'inlineXML', attrib={'contenttype': 'application/xhtml+xml'})
        inline.append(self._build_html_doc(article))

    def _build_html_doc(self, article):
        try:
            html = etree.HTML(article.get('body_html'))
        except etree.XMLSyntaxError:
            html = etree.HTML('<p></p>')
        return html

    def can_format(self, format_type, article):
        """Method check if the article can be formatted to NewsML G2 or not.

        :param str format_type:
        :param dict article:
        :return: True if article can formatted else False
        """
        return format_type == 'newsmlg2'

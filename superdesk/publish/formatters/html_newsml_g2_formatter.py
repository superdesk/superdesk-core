
import xml.etree.ElementTree as etree

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
        inline = etree.SubElement(content_set, 'inlineXML',
                                  attrib={'contenttype': 'application/xhtml+xml'})

        inline.append(self._build_html_doc(article))

    def _build_html_doc(self, article):
        doc = etree.Element('html', attrib=self._message_attrib)
        head = etree.SubElement(doc, 'head')
        title = etree.SubElement(head, 'title')
        title.text = article.get('headline')
        body = etree.SubElement(doc, 'body')
        contents = etree.fromstring(article.get('body_html'))
        body.append(contents)
        return doc

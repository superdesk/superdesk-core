# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from lxml import etree
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, FORMATS, FORMAT
from superdesk.metadata.utils import is_takes_package
from superdesk.etree import parse_html, get_text

formatters = []
logger = logging.getLogger(__name__)


class FormatterRegistry(type):
    """Registry metaclass for formatters."""

    def __init__(cls, name, bases, attrs):
        """Register sub-classes of Formatter class when defined."""
        super(FormatterRegistry, cls).__init__(name, bases, attrs)
        if name != 'Formatter':
            formatters.append(cls())


class Formatter(metaclass=FormatterRegistry):
    """Base Formatter class for all types of Formatters like News ML 1.2, News ML G2, NITF, etc."""

    def __init__(self):
        self.can_preview = False
        self.can_export = False

    def format(self, article, subscriber, codes=None):
        """Formats the article and returns the transformed string"""
        raise NotImplementedError()

    def export(self, article, subscriber, codes=None):
        """Formats the article and returns the output string for export"""
        raise NotImplementedError()

    def can_format(self, format_type, article):
        """Test if formatter can format for given article."""
        raise NotImplementedError()

    def append_body_footer(self, article):
        """
        Checks if the article has any Public Service Announcements and if available appends each of them to the body.

        :return: body with public service announcements.
        """
        try:
            article['body_html'] = article['body_html'].replace('<br>', '<br/>')
        except KeyError:
            pass

        body = ''
        if article[ITEM_TYPE] in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED] or is_takes_package(article):
            body = article.get('body_html', '')
        elif article[ITEM_TYPE] in [CONTENT_TYPE.AUDIO, CONTENT_TYPE.PICTURE, CONTENT_TYPE.VIDEO]:
            body = article.get('description', '')

        if body and article.get(FORMAT, '') == FORMATS.PRESERVED:
            body = body.replace('\n', '\r\n').replace('\r\r', '\r')
            parsed = parse_html(body, content='html')

            for br in parsed.xpath('//br'):
                br.tail = '\r\n' + br.tail if br.tail else '\r\n'

            etree.strip_elements(parsed, 'br', with_tail=False)
            body = etree.tostring(parsed, encoding="unicode")

        if body and article.get('body_footer'):
            footer = article.get('body_footer')
            if article.get(FORMAT, '') == FORMATS.PRESERVED:
                body = '{}\r\n{}'.format(body, get_text(footer))
            else:
                body = '{}{}'.format(body, footer)
        return body

    def append_legal(self, article, truncate=False):
        """
        Checks if the article has the legal flag on and adds 'Legal:' to the slugline

        :param article: article having the slugline
        :param truncate: truncates the slugline to 24 characters
        :return: updated slugline
        """
        slugline = article.get('slugline', '') or ''

        if article.get('flags', {}).get('marked_for_legal', False):
            slugline = '{}: {}'.format('Legal', slugline)
            if truncate:
                slugline = slugline[:24]

        return slugline

    def map_html_to_xml(self, element, html):
        """
        Map the html text tags to xml

        :param etree.Element element: The xml element to populate
        :param str html: the html to parse the text from
        :return:
        """
        root = parse_html(html)
        # if there are no ptags just br
        if not len(root.xpath('//p')) and len(root.xpath('//br')):
            para = etree.SubElement(element, 'p')
            for br in root.xpath('//br'):
                etree.SubElement(para, 'br').text = br.text

        for p in root.xpath('//p'):
            para = etree.SubElement(element, 'p')
            if len(p.xpath('.//br')) > 0:
                for br in p.xpath('.//br'):
                    etree.SubElement(para, 'br').text = br.text
            para.text = etree.tostring(p, encoding="unicode", method="text")

        # there neither ptags pr br's
        if len(list(element)) == 0:
            etree.SubElement(element, 'p').text = etree.tostring(root, encoding="unicode", method="text")


def get_formatter(format_type, article):
    """Get parser for given xml.

    :param etree: parsed xml
    """
    for formatter in formatters:
        if formatter.can_format(format_type, article):
            return formatter


def get_all_formatters():
    """Return all formatters registered."""
    return formatters


from .nitf_formatter import NITFFormatter  # NOQA
from .ninjs_formatter import NINJSFormatter  # NOQA
from .newsml_1_2_formatter import NewsML12Formatter  # NOQA
from .newsml_g2_formatter import NewsMLG2Formatter  # NOQA
from .email_formatter import EmailFormatter  # NOQA

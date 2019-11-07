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
from superdesk.etree import parse_html
from superdesk.text_utils import get_text
from superdesk.publish import registered_transmitters

formatters = []
logger = logging.getLogger(__name__)


class FormatterRegistry(type):
    """Registry metaclass for formatters."""

    def __init__(cls, name, bases, attrs):
        """Register sub-classes of Formatter class when defined."""
        super(FormatterRegistry, cls).__init__(name, bases, attrs)
        if name != 'Formatter':
            formatters.append(cls)


class Formatter(metaclass=FormatterRegistry):
    """Base Formatter class for all types of Formatters like News ML 1.2, News ML G2, NITF, etc."""

    def __init__(self):
        self.can_preview = False
        self.can_export = False
        self.destination = None
        self.subscriber = None

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
        if article[ITEM_TYPE] in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
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
        root = parse_html(html, content='html')
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

    def set_destination(self, destination=None, subscriber=None):
        self.destination = destination
        self.subscriber = subscriber

    def _publish_media(self, media):
        if self.destination:
            try:
                transmitter = registered_transmitters[self.destination['delivery_type']]
            except KeyError:
                logger.warning('Missing transmitter for destination %s', self.destination)
            else:
                return transmitter.transmit_media(media, self.subscriber, self.destination)


def get_formatter(format_type, article):
    for formatter_cls in formatters:
        formatter_instance = formatter_cls()
        if formatter_instance.can_format(format_type, article):
            return formatter_instance


def get_all_formatters():
    """Return all formatters registered."""
    return [formatter_cls() for formatter_cls in formatters]


from .nitf_formatter import NITFFormatter  # NOQA
from .ninjs_formatter import NINJSFormatter, NINJS2Formatter  # NOQA
from .newsml_1_2_formatter import NewsML12Formatter  # NOQA
from .newsml_g2_formatter import NewsMLG2Formatter  # NOQA
from .email_formatter import EmailFormatter  # NOQA
from .ninjs_newsroom_formatter import NewsroomNinjsFormatter  # NOQA
from .idml_formatter import IDMLFormatter  # NOQA

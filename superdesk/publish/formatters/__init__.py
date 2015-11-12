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

from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE

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

    def format(self, article, subscriber):
        """Formats the article and returns the transformed string"""
        raise NotImplementedError()

    def can_format(self, format_type, article):
        """Test if formatter can format for given article."""
        raise NotImplementedError()

    def append_public_service_announcements(self, article):
        """
        Checks if the article has any Public Service Announcements and if available appends each of them to the body.

        :return: body with public service announcements.
        """

        body = ''
        if article[ITEM_TYPE] in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            body = article.get('body_html', '')
        elif article[ITEM_TYPE] in [CONTENT_TYPE.AUDIO, CONTENT_TYPE.PICTURE, CONTENT_TYPE.VIDEO]:
            body = article.get('description', '')

        if body and article.get('psa_footers'):
            for footer in article['psa_footers']:
                body = '{}<br>{}'.format(body, footer['value'])

        return body


def get_formatter(format_type, article):
    """Get parser for given xml.

    :param etree: parsed xml
    """
    for formatter in formatters:
        if formatter.can_format(format_type, article):
            return formatter


import superdesk.publish.formatters.nitf_formatter  # NOQA
import superdesk.publish.formatters.ninjs_formatter  # NOQA
import superdesk.publish.formatters.newsml_1_2_formatter  # NOQA

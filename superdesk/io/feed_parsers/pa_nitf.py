#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers.nitf import NITFFeedParser, SkipValue
from superdesk.io import register_feed_parser
import re


class PAFeedParser(NITFFeedParser):
    """
    NITF Parser extension for Press Association, it maps the category meta tag to an anpa category
    """

    NAME = 'pa_nitf'

    def _category_mapping(self, elem):
        """Map the category supplied by PA to a best guess anpa_category in the system

        :param elem:
        :return: anpa category list qcode
        """
        if elem.get('content') is not None:
            category = elem.get('content')[:1].upper()
            if category in {'S', 'R', 'F'}:
                return [{'qcode': 'S'}]
            if category == 'Z':
                return [{'qcode': 'V'}]
        return [{'qcode': 'I'}]

    def get_headline(self, xml):
        """Return the headline if available if not then return the slugline (title)

        :param xml:
        :return:
        """
        if xml.find('body/body.head/hedline/hl1') is not None:
            return xml.find('body/body.head/hedline/hl1').text
        else:
            if xml.find('head/title') is not None:
                return self._get_slugline(xml.find('head/title'))
        raise SkipValue()

    def _get_slugline(self, elem):
        """Capitalize the first word of the slugline (Removing any leading digits's).

        :param elem:
        :return:
        """
        # Remove any leading numbers and split to list of words
        sluglineList = re.sub('^[\d.]+\W+', '', elem.text).split(' ')
        slugline = sluglineList[0].capitalize()
        if len(sluglineList) > 1:
            slugline = '{} {}'.format(slugline, ' '.join(sluglineList[1:]))
        return slugline

    def _get_pubstatus(self, elem):
        """Mark anything that is embargoed as usable, the editorial note still describes the embargo.

        :param elem:
        :return:
        """
        return 'usable' if elem.attrib['management-status'] == 'embargoed' else elem.attrib['management-status']

    def __init__(self):
        self.MAPPING = {'anpa_category': {'xpath': "head/meta/[@name='category']", 'filter': self._category_mapping},
                        'slugline': {'xpath': 'head/title', 'filter': self._get_slugline},
                        'pubstatus': {'xpath': 'head/docdata', 'filter': self._get_pubstatus}}
        super().__init__()

register_feed_parser(PAFeedParser.NAME, PAFeedParser())

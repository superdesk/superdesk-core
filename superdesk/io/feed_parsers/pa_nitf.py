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

from superdesk.io.feed_parsers.nitf import NITFFeedParser
from superdesk.io import register_feed_parser


class PAFeedParser(NITFFeedParser):
    """
    NITF Parser extension for Press Association, it maps the category meta tag to an anpa category
    """
    NAME = 'pa_nitf'

    def _category_mapping(self, elem):
        """
        Map the category supplied by PA to a best guess anpa_category in the system
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

    def __init__(self):
        self.MAPPING = {'anpa_category': {'xpath': "head/meta/[@name='category']", 'filter': self._category_mapping}}
        super().__init__()

register_feed_parser(PAFeedParser.NAME, PAFeedParser())

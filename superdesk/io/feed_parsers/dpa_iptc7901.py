
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .iptc7901 import IPTC7901FeedParser
from superdesk.io import register_feed_parser
from flask import current_app as app
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE


class DPAIPTC7901FeedParser(IPTC7901FeedParser):

    NAME = 'dpa_iptc7901'

    def parse(self, file_path, provider=None):
        item = super().parse(file_path, provider)
        item = self.dpa_derive_dateline(item)
        # Markup the text and set the content type
        item['body_html'] = '<p>' + item['body_html'].replace('\r\n', ' ').replace('\n', '</p><p>') + '</p>'
        item[ITEM_TYPE] = CONTENT_TYPE.TEXT
        return item

    def dpa_derive_dateline(self, item):
        """Parse dateline from item body.

        This function attempts to parse a dateline from the first few lines of
        the item body and populate the dataline location, it also populates the dateline source.
        If a dateline is matched the coresponding string is removed from the article text.

        :param item:
        :return:
        """
        lines = item['body_html'].splitlines()
        if lines:
            # expect the dateline in the first 5 lines, sometimes there is what appears to be a headline preceeding it.
            for line_num in range(0, min(len(lines), 5)):
                city, source, the_rest = lines[line_num].partition(' (dpa) - ')
                # test if we found a candidate and ensure that the city starts the line and is not crazy long
                if source and lines[line_num].find(city) == 0 and len(city.strip()) < 20:
                    cities = app.locators.find_cities()
                    located = [c for c in cities if c['city'].lower() == city.strip().lower()]
                    if 'dateline' not in item:
                        item['dateline'] = {}
                    item['dateline']['located'] = located[0] if len(located) > 0 else {'city_code': city.strip(),
                                                                                       'city': city.strip(),
                                                                                       'tz': 'UTC', 'dateline': 'city'}
                    item['dateline']['source'] = 'dpa'
                    item['dateline']['text'] = city.strip()
                    item['body_html'] = item['body_html'].replace(city + source, '', 1)
                    break
        return item

register_feed_parser(DPAIPTC7901FeedParser.NAME, DPAIPTC7901FeedParser())

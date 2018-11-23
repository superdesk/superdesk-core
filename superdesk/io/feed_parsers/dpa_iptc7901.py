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
from superdesk.io.registry import register_feed_parser
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE


class DPAIPTC7901FeedParser(IPTC7901FeedParser):
    NAME = 'dpa_iptc7901'

    label = 'DPA IPTC 7901 Parser'

    def parse(self, file_path, provider=None):
        item = super().parse(file_path, provider)
        item = self.dpa_derive_dateline(item)
        self.dpa_parse_header(item)
        # Markup the text and set the content type
        item['body_html'] = '<p>' + item['body_html'].replace('\r\n', ' ').replace('\n', '</p><p>') + '</p>'
        item[ITEM_TYPE] = CONTENT_TYPE.TEXT
        return item

    def dpa_parse_header(self, item):
        """
        Try to pickout the headline, byline and take key from what is seemingly a header
        :param item:
        :return:
        """
        headers, divider, the_rest = item.get('body_html', '').partition(' =\r\n\n')
        # If no divider then there was only one line and that is the headline so clean up the stray '='
        if not divider:
            item['headline'] = item.get('headline').replace(' =', '')
            return

        headerlines = headers.split('\n')

        # If the last one is a byline, the line before is the headline
        if headerlines[-1].startswith('By '):
            item['byline'] = headerlines[-1].replace('By ', '')
            if len(headerlines) > 1:
                item['anpa_take_key'] = item.get('headline') if item.get('anpa_take_key') is None else item.get(
                    'anpa_take_key') + ' ' + item.get('headline')
                item['headline'] = headerlines[-2]
            if len(headerlines) > 2:
                item['anpa_take_key'] = headerlines[-3] if item.get('anpa_take_key') is None else item.get(
                    'anpa_take_key') + ' ' + headerlines[-3]
            item['body_html'] = the_rest
            return

        # Only a headline
        if len(headerlines) == 1:
            item['anpa_take_key'] = item.get('headline') if item.get('anpa_take_key') is None \
                else item.get('anpa_take_key') + ' ' + item.get('headline')
            item['headline'] = headerlines[-1]
            item['body_html'] = the_rest
            return

        # Take the headline as the last one and any preceding into the take key
        item['headline'] = headerlines[-1]
        if len(headerlines) > 1:
            item['anpa_take_key'] = headerlines[-2] if item.get('anpa_take_key') is None \
                else item.get('anpa_take_key') + ' ' + headerlines[-2]
        item['body_html'] = the_rest

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
                    self.set_dateline(item, city.strip())
                    item['dateline']['source'] = 'dpa'
                    item['dateline']['text'] = city.strip()
                    item['body_html'] = item['body_html'].replace(city + source, '', 1)
                    break
        return item


register_feed_parser(DPAIPTC7901FeedParser.NAME, DPAIPTC7901FeedParser())


# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import pytz
import datetime
from .newsml_2_0 import NewsMLTwoFeedParser
from superdesk.io import register_feed_parser
from superdesk.errors import ParserError
from superdesk.metadata.item import ITEM_TYPE
from superdesk.io.iptc import subject_codes
from superdesk.etree import get_word_count


class ScoopNewsMLTwoFeedParser(NewsMLTwoFeedParser):

    NAME = 'scoop_newsml2'

    def can_parse(self, xml):
        if xml.tag.endswith('newsMessage'):
            try:
                self.root = xml
                header = xml.find(self.qname('Header'))
                origin = header.find(self.qname('origin')).text
                if origin == 'BusinessDesk':
                    return True
            except:
                return False
        return False

    def parse(self, xml, provider=None):
        self.root = xml
        items = []
        try:
            header = self.parse_header(xml)
            for item_set in xml.findall(self.qname('itemSet')):
                for item_tree in item_set:
                    # Ignore the packageItem, it has no guid
                    if 'guid' in item_tree.attrib:
                        item = self.parse_item(item_tree)
                        item['priority'] = header['priority']
                        item['anpa_category'] = [{'qcode': 'f'}]
                        item['subject'] = [{'qcode': '04000000', 'name': subject_codes['04000000']}]
                        item.setdefault('word_count', get_word_count(item['body_html']))
                        items.append(item)
            return items
        except Exception as ex:
            raise ParserError.newsmlTwoParserError(ex, provider)

    def parse_header(self, tree):
        """Parse header element, it seems that the header tag is in camel case

        :param tree:
        :return: dict
        """
        header = tree.find(self.qname('Header'))
        priority = 5
        if header:
            priority = self.map_priority(header.find(self.qname('priority')).text)

        return {'priority': priority}

    def parse_item_meta(self, tree, item):
        """Parse itemMeta tag"""
        meta = tree.find(self.qname('itemMeta'))
        item[ITEM_TYPE] = meta.find(self.qname('itemClass')).attrib['qcode'].split(':')[1]
        item['versioncreated'] = self.datetime(meta.find(self.qname('versionCreated')).text)
        item['firstcreated'] = item['versioncreated']
        item['pubstatus'] = (meta.find(self.qname('pubStatus')).attrib['qcode'].split(':')[1]).lower()
        item['ednote'] = meta.find(self.qname('edNote')).text if meta.find(self.qname('edNote')) is not None else ''

    def datetime(self, string):
        """Convert the date string parsed from the source file to a datetime, assumes that the time is local to NZ

        :param string:
        :return:
        """
        local_dt = datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
        local_tz = pytz.timezone('Pacific/Auckland')
        nz_dt = local_tz.localize(local_dt, is_dst=None)
        return nz_dt.astimezone(pytz.utc)

    def parse_content_set(self, tree, item):
        """Parse out the nitf like content.

        :param tree:
        :param item:
        :return: item populated with a headline and body_html
        """
        for content in tree.find(self.qname('contentSet')):
            if content.tag == self.qname('inlineXML') and content.attrib['contenttype'] == 'application/nitf+xml':
                nitf = content.find(self.qname('nitf'))
                head = nitf.find(self.qname('head'))
                item['headline'] = head.find(self.qname('title')).text
                body = nitf.find(self.qname('body'))
                content = self.parse_inline_content(body)
                item['body_html'] = content.get('content')

    def parse_inline_content(self, tree):
        body = tree.find(self.qname('body.content'))
        elements = []
        for elem in body:
            if elem.text:
                tag = elem.tag.rsplit('}')[1]
                elements.append('<%s>%s</%s>' % (tag, elem.text, tag))

        content = dict()
        content['content'] = "\n".join(elements)
        return content

register_feed_parser(ScoopNewsMLTwoFeedParser.NAME, ScoopNewsMLTwoFeedParser())

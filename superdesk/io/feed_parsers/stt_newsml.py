# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers.newsml_2_0 import NewsMLTwoFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.errors import ParserError
from superdesk.metadata.item import CONTENT_TYPE
from superdesk import etree as sd_etree
import logging

logger = logging.getLogger(__name__)
IPTC_NS = 'http://iptc.org/std/nar/2006-10-01/'


class STTNewsMLFeedParser(NewsMLTwoFeedParser):
    """
    Feed Parser which can parse STT variant of NewsML
    """

    NAME = 'sttnewsml'
    label = "STT NewsML"
    SUBJ_QCODE_PREFIXES = ('stt-subj',)

    def can_parse(self, xml):
        return xml.tag.endswith('newsItem')

    def parse(self, xml, provider=None):
        self.root = xml
        try:
            item = self.parse_item(xml)
            return [item]
        except Exception as ex:
            raise ParserError.newsmlTwoParserError(ex, provider)

    def parse_inline_content(self, tree, item):
        html_elt = tree.find(self.qname('html'))
        body_elt = html_elt.find(self.qname('body'))
        body_elt = sd_etree.clean_html(body_elt)

        content = dict()
        content['contenttype'] = tree.attrib['contenttype']
        if len(body_elt) > 0:
            contents = [sd_etree.to_string(e, encoding='unicode', method="html") for e in body_elt]
            content['content'] = '\n'.join(contents)
        elif body_elt.text:
            content['content'] = '<pre>' + body_elt.text + '</pre>'
            content['format'] = CONTENT_TYPE.PREFORMATTED
        return content


register_feed_parser(STTNewsMLFeedParser.NAME, STTNewsMLFeedParser())

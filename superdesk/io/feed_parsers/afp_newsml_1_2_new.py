# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024, Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers.newsml_1_2 import NewsMLOneFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.etree import etree


class AFPNewsMLFeedParser(NewsMLOneFeedParser):
    """AFP specific NewsML parser.

    Feed Parser which can parse the AFP feed basically it is in NewsML 1.0 format,
    """

    NAME = "afpnewsmlnew"

    label = "AFP News ML New Parser"

    def can_parse(self, xml):
        return xml.tag == "NewsML"

    def parse_content(self, item, xml):
        item["body_html"] = (
            etree.tostring(
                xml.find("NewsItem/NewsComponent/NewsComponent/ContentItem/DataContent"),
                encoding="unicode",
            )
            .replace("<DataContent>", "")
            .replace("</DataContent>", "")
            .strip()
        )


register_feed_parser(AFPNewsMLFeedParser.NAME, AFPNewsMLFeedParser())

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024, Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers.newsml_2_0 import NewsMLTwoFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.etree import etree
from superdesk.utc import utcnow
from pytz import utc


class DPAFeedParser(NewsMLTwoFeedParser):
    """DPA specific NewsML parser.

    Feed Parser which can parse the DPA feed basically it is in NewsML 1.0 format,
    """

    NAME = "dpanewsml"

    label = "DPA News ML Parser"

    missing_voc = None

    def can_parse(self, xml):
        return super().can_parse(xml)

    def parse(self, xml, provider=None):
        items = super().parse(xml, provider)
        for item in items:
            if "versioncreated" in item:
                item["versioncreated"] = item["versioncreated"].astimezone(utc)
            if "firstcreated" in item:
                item["firstcreated"] = item["firstcreated"].astimezone(utc)
        return items


register_feed_parser(DPAFeedParser.NAME, DPAFeedParser())

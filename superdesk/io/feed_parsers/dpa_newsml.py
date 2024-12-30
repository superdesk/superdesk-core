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
from pytz import utc
import re


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

    def parse_content_set(self, tree, item):
        super().parse_content_set(tree, item)

        xhtml_ns = "http://www.w3.org/1999/xhtml"
        section_class = "dpatextgenre-7"

        content_set = tree.find(self.qname("contentSet"))
        if content_set is None:
            return

        for content in content_set:
            if content.tag != self.qname("inlineXML"):
                continue

            html_content = content.find(self.qname("html", xhtml_ns))
            if html_content is None:
                continue

            body = html_content.find(self.qname("body", xhtml_ns))
            if body is None:
                continue

            section = body.find(self.qname("section", xhtml_ns))
            if section is None:
                continue

            body_html = etree.tostring(section, encoding="unicode", method="html")
            body_html = re.sub(
                r'<section[^>]*class="[^"]*{}[^"]*"[^>]*>'.format(re.escape(section_class)), "", body_html
            )
            body_html = body_html.replace("</section>", "")

            item["body_html"] = body_html


register_feed_parser(DPAFeedParser.NAME, DPAFeedParser())

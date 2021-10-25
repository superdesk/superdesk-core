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
from superdesk.io.registry import register_feed_parser
import re
from lxml import etree
import html


class PAFeedParser(NITFFeedParser):
    """
    NITF Parser extension for Press Association, it maps the category meta tag to an anpa category
    """

    NAME = "pa_nitf"

    label = "PA NITF"

    def _category_mapping(self, elem):
        """Map the category supplied by PA to a best guess anpa_category in the system.

        There is a special case for the incomming category 'HHH' is to check the doc-scope for SHOWBIZ, if present the
        category is set to Entertainment

        :param elem:
        :return: anpa category list qcode
        """
        if elem.get("content") is not None:
            category = elem.get("content")[:1].upper()
            if category in {"S", "R", "F"}:
                return [{"qcode": "S"}]
            if category == "Z":
                return [{"qcode": "V"}]
            if category == "H":
                if self.xml.find("head/docdata/doc-scope[@scope='SHOWBIZ']") is not None:
                    return [{"qcode": "E"}]
        return [{"qcode": "I"}]

    def get_content(self, xml):
        """Get the body content of the item.

        Remove the child tags of the p tags such as location, person etc. These have no meaning in the editor at the
        moment. Also handle the encoding, for example the £ symbol in the body text.

        :param xml:
        :return:
        """
        elements = []
        for elem in xml.find("body/body.content"):
            text = etree.tostring(elem, encoding="unicode", method="text")
            elements.append("<p>{}</p>\n".format(html.escape(text)))
        content = "".join(elements)
        if self.get_anpa_format(xml) == "t":
            if not content.startswith("<pre>"):
                # convert content to text in a pre tag
                content = "<pre>{}</pre>".format(self.parse_to_preformatted(content))
            else:
                content = self.parse_to_preformatted(content)
        return content

    def get_headline(self, xml):
        """Return the headline if available if not then return the slugline (title)

        :param xml:
        :return:
        """
        if xml.find("body/body.head/hedline/hl1") is not None:
            return xml.find("body/body.head/hedline/hl1").text
        else:
            if xml.find("head/title") is not None:
                return self._get_slugline(xml.find("head/title"))
        raise SkipValue()

    def _get_slugline(self, elem):
        """Capitalize the first word of the slugline (Removing any leading digits's).

        :param elem:
        :return:
        """
        # Remove any leading numbers and split to list of words
        sluglineList = re.sub(r"^[\d.]+\W+", "", elem.text).split(" ")
        slugline = sluglineList[0].capitalize()
        if len(sluglineList) > 1:
            slugline = "{} {}".format(slugline, " ".join(sluglineList[1:]))
        return slugline

    def _get_pubstatus(self, elem):
        """Mark anything that is embargoed as usable, the editorial note still describes the embargo.

        :param elem:
        :return:
        """
        return "usable" if elem.attrib["management-status"] == "embargoed" else elem.attrib["management-status"]

    def __init__(self):
        self.MAPPING = {
            "anpa_category": {"xpath": "head/meta[@name='category']", "filter": self._category_mapping},
            "slugline": {"xpath": "head/title", "filter": self._get_slugline},
            "pubstatus": {"xpath": "head/docdata", "filter": self._get_pubstatus},
        }
        super().__init__()

    def parse(self, xml, provider=None):
        self.xml = xml
        return super().parse(xml, provider=provider)


register_feed_parser(PAFeedParser.NAME, PAFeedParser())

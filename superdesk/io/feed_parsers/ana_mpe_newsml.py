# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import datetime
import pytz
from superdesk.etree import etree
import html
from superdesk.io.feed_parsers.newsml_1_2 import NewsMLOneFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.errors import ParserError
from dateutil.parser import parse as date_parser
from flask import current_app as app
from apps.archive.common import format_dateline_to_locmmmddsrc


class ANANewsMLOneFeedParser(NewsMLOneFeedParser):
    """ANA specific NewsML parser.

    Feed Parser which can parse the ANA English feed basically it is in NewsML 1.2 format
    """

    NAME = "ananewsml12"

    label = "ANA NewsML Parser"

    def can_parse(self, xml):
        return xml.tag == "NewsML"

    def parse(self, xml, provider=None):
        item = {}
        try:
            self.root = xml
            parsed_el = xml.find("NewsItem/NewsComponent/AdministrativeMetadata/Source/Party")
            if parsed_el is not None:
                item["original_source"] = parsed_el.attrib.get("FormalName", "ANA")

            parsed_el = xml.find("NewsEnvelope/Priority")
            item["priority"] = self.map_priority(parsed_el.text if parsed_el is not None else None)

            self.parse_news_identifier(item, xml)
            self.parse_newslines(item, xml)
            self.parse_news_management(item, xml)

            parsed_el = xml.findall("NewsItem/NewsComponent/DescriptiveMetadata/Language")
            if parsed_el is not None:
                language = self.parse_attributes_as_dictionary(parsed_el)
                item["language"] = language[0]["FormalName"] if len(language) else ""

            subjects = xml.findall(
                'NewsItem/NewsComponent/DescriptiveMetadata/SubjectCode/SubjectDetail[@Scheme="IptcSubjectCodes"]'
            )
            subjects += xml.findall(
                'NewsItem/NewsComponent/DescriptiveMetadata/SubjectCode/SubjectMatter[@Scheme="IptcSubjectCodes"]'
            )
            subjects += xml.findall(
                'NewsItem/NewsComponent/DescriptiveMetadata/SubjectCode/Subject[@Scheme="IptcSubjectCodes"]'
            )

            item["subject"] = self.format_subjects(subjects)

            item["body_html"] = (
                html.unescape(
                    etree.tostring(
                        xml.find("NewsItem/NewsComponent/NewsComponent/ContentItem/DataContent"), encoding="unicode"
                    )
                )
                .replace("<DataContent>", "")
                .replace("</DataContent>", "")
                .replace("<P>", "<p>")
                .replace("</P>", "</p>")
            )

            item["body_html"] = (
                item.get("body_html")
                .replace(
                    "<p>© ΑΠΕ-ΜΠΕ ΑΕ. Τα πνευματικά δικαιώματα ανήκουν στο "
                    "ΑΠΕ-ΜΠΕ ΑΕ και παραχωρούνται σε συνδρομητές μόνον "
                    "για συγκεκριμένη χρήση.</p>",
                    "",
                )
                .strip()
            )
            parsed_el = xml.findall("NewsItem/NewsComponent/NewsComponent/ContentItem/Characteristics/Property")
            characteristics = self.parse_attribute_values(parsed_el, "WordCount")
            item["word_count"] = characteristics[0] if len(characteristics) else None

            # Extract the city for setting into the dateline
            city = xml.find('NewsItem/NewsComponent/DescriptiveMetadata/Property[@FormalName="City"]').attrib.get(
                "Value"
            )
            # Anglicise the greek for Athens if required
            city = "Athens" if city == "Αθήνα" else city
            country = xml.find('NewsItem/NewsComponent/DescriptiveMetadata/Property[@FormalName="Country"]').attrib.get(
                "Value"
            )
            # Normalise the country code
            country = "GR" if country == "GRC" else country

            cities = app.locators.find_cities()
            located = [c for c in cities if c["city"] == city and c["country_code"] == country]
            if len(located) == 1:
                item["dateline"]["located"] = located[0]
                item["dateline"]["source"] = provider.get("source")
                item["dateline"]["text"] = format_dateline_to_locmmmddsrc(
                    item["dateline"]["located"], item.get("dateline", {}).get("date"), provider.get("source")
                )
            return self.populate_fields(item)
        except Exception as ex:
            raise ParserError.newsmlOneParserError(ex, provider)

    def parse_newslines(self, item, tree):
        parsed_el = self.parse_elements(tree.find("NewsItem/NewsComponent/NewsLines"))

        # Set the date component of the dateline assuming that the date is in the Athens timezone
        local_dt = date_parser(parsed_el.get("DateLine", ""), fuzzy=True, dayfirst=True)
        local_tz = pytz.timezone("Europe/Athens")
        aus_dt = local_tz.localize(local_dt, is_dst=None)
        item.setdefault("dateline", {})
        item["dateline"]["date"] = aus_dt.astimezone(pytz.utc)

        item["headline"] = parsed_el.get("HeadLine", "").strip()
        item["slugline"] = parsed_el.get("SlugLine", "")
        # The byline is not extracted as it seems to use the Greek character set

        return True

    def parse_news_management(self, item, tree):
        parsed_el = self.parse_elements(tree.find("NewsItem/NewsManagement"))
        item["urgency"] = int(parsed_el.get("Urgency", {}).get("FormalName", 3))
        item["versioncreated"] = self.datetime(parsed_el["ThisRevisionCreated"])
        item["firstcreated"] = self.datetime(parsed_el["FirstCreated"])
        item["pubstatus"] = (parsed_el["Status"]["FormalName"]).lower()

    def datetime(self, string):
        try:
            return datetime.datetime.strptime(string, "%Y%m%dT%H%M%S%z")
        except ValueError:
            return super().datetime(string)


register_feed_parser(ANANewsMLOneFeedParser.NAME, ANANewsMLOneFeedParser())

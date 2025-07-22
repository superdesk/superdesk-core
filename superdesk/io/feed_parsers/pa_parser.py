# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime
from superdesk.utc import utc
from superdesk.etree import etree
from superdesk.errors import ParserError
from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE


class PAParser(XMLFeedParser):
    """
    Feed Parser for PA (Press Association) XML files.
    """

    NAME = "pa_parser"
    label = "PA Parser"

    def can_parse(self, xml):
        try:
            return xml.tag == "NewsML" and xml.find(".//nitf") is not None
        except AttributeError:
            return False

    def parse(self, xml, provider=None):
        try:
            item = {}
            self.root = xml

            self.parse_news_envelope(xml, item)
            self.parse_identification(xml, item)
            self.parse_news_management(xml, item)
            self.parse_newslines(xml, item)
            self.parse_descriptive_metadata(xml, item)
            self.parse_rights_metadata(xml, item)
            self.parse_content(xml, item)
            self.parse_embargo(xml, item)

            item[ITEM_TYPE] = CONTENT_TYPE.TEXT

            if "guid" not in item:
                item["guid"] = f"pa-{datetime.now().timestamp()}"
            if "headline" not in item:
                item["headline"] = "No headline available"
            if "versioncreated" not in item:
                item["versioncreated"] = datetime.now(tz=utc)

            return item
        except Exception as ex:
            raise ParserError.parseFileError(exception=ex, provider=provider)

    def parse_news_envelope(self, tree, item):
        envelope = tree.find("NewsEnvelope")
        if envelope is not None:
            sent_from = envelope.find("SentFrom/Party")
            if sent_from is not None:
                item["original_source"] = sent_from.get("FormalName", "")

            date_and_time = envelope.find("DateAndTime")
            if date_and_time is not None and date_and_time.text:
                item["firstcreated"] = self.parse_datetime(date_and_time.text)

            priority = envelope.find("Priority")
            if priority is not None:
                item["priority"] = self.map_priority(priority.get("FormalName"))

    def parse_identification(self, tree, item):
        """Parse NewsItem identification with version number handling."""
        news_id = tree.find("NewsItem/Identification/NewsIdentifier")
        if news_id is not None:
            provider_id = news_id.find("ProviderId")
            if provider_id is not None and provider_id.text:
                item["ingest_provider"] = provider_id.text

            public_id = news_id.find("PublicIdentifier")
            if public_id is not None and public_id.text:
                item["guid"] = public_id.text

            revision = news_id.find("RevisionId")
            if revision is not None:
                if revision.get("PreviousRevision"):
                    item["previous_version"] = str(revision.get("PreviousRevision"))

    def parse_news_management(self, tree, item):
        mgmt = tree.find("NewsItem/NewsManagement")
        if mgmt is not None:
            first_created = mgmt.find("FirstCreated")
            if first_created is not None and first_created.text:
                item["firstcreated"] = self.parse_datetime(first_created.text)

            this_revision = mgmt.find("ThisRevisionCreated")
            if this_revision is not None and this_revision.text:
                item["versioncreated"] = self.parse_datetime(this_revision.text)

            status = mgmt.find("Status")
            if status is not None:
                item["pubstatus"] = status.get("FormalName", "").lower()

            urgency = mgmt.find("Urgency")
            if urgency is not None:
                item["urgency"] = int(urgency.get("FormalName", 5))

            news_item_type = mgmt.find("NewsItemType")
            if news_item_type is not None:
                item["type"] = news_item_type.get("FormalName", "")

    def parse_newslines(self, tree, item):
        newslines = tree.find("NewsItem/NewsComponent/NewsLines")
        if newslines is not None:
            headline = newslines.find("HeadLine")
            if headline is not None and headline.text:
                item["headline"] = headline.text

            byline = newslines.find("ByLine")
            if byline is not None and byline.text:
                item["byline"] = byline.text

            slugline = newslines.find("SlugLine")
            if slugline is not None and slugline.text:
                item["slugline"] = slugline.text

            copyright_line = newslines.find("CopyrightLine")
            if copyright_line is not None and copyright_line.text:
                item["copyrightnotice"] = copyright_line.text

    def parse_descriptive_metadata(self, tree, item):
        """Parse DescriptiveMetadata section with proper ANPA category handling."""
        desc_meta = tree.find("NewsItem/NewsComponent/DescriptiveMetadata")
        if desc_meta is not None:
            subjects = []
            for prop in desc_meta.findall("Property[@FormalName='Topic']"):
                subjects.append({"name": prop.get("Value"), "qcode": prop.get("Value"), "scheme": "topics"})
            if subjects:
                item["subject"] = subjects

            keywords = []
            for prop in desc_meta.findall("Property[@FormalName='Keyword']"):
                keywords.append(prop.get("Value"))
            if keywords:
                item["keywords"] = keywords

            category = desc_meta.find("Property[@FormalName='Category']")
            if category is not None:
                category_value = category.get("Value")
                item["anpa_category"] = [
                    {
                        "name": category_value,
                        "qcode": category_value,
                    }
                ]

    def parse_rights_metadata(self, tree, item):
        rights = tree.find("NewsItem/NewsComponent/RightsMetadata/Copyright")
        if rights is not None:
            holder = rights.find("CopyrightHolder")
            if holder is not None and holder.text:
                item["copyrightnotice"] = holder.text

            date = rights.find("CopyrightDate")
            if date is not None and date.text:
                item[
                    "copyrightholder"
                ] = f"{holder.text if holder is not None and holder.text else ''} {date.text}".strip()

    def parse_content(self, tree, item):
        content = tree.find(".//body.content")
        if content is not None:
            body_html = etree.tostring(content, encoding="unicode", method="html")
            body_html = body_html.replace("<body.content>", "").replace("</body.content>", "")
            wrapped_html = f"<div>{body_html}</div>"
            parser = etree.HTMLParser()
            cleaned_tree = etree.fromstring(wrapped_html, parser)
            etree.strip_tags(cleaned_tree, "chron", "org", "location", "person")
            item["body_html"] = "".join(
                etree.tostring(child, encoding="unicode", method="html") for child in cleaned_tree.xpath("body/div/*")
            )

    def parse_embargo(self, tree, item):
        comment = tree.find(".//Comment")
        if comment is not None and comment.text and "Embargoed" in comment.text:
            item["embargo"] = self.parse_embargo_text(comment.text)

    def parse_embargo_text(self, text):
        return text.strip()

    def parse_datetime(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y%m%dT%H%M%S%z")
        except ValueError:
            return datetime.strptime(date_str[:14], "%Y%m%dT%H%M%S").replace(tzinfo=utc)

    def map_priority(self, priority):
        try:
            return int(priority)
        except (ValueError, TypeError):
            return 5


register_feed_parser(PAParser.NAME, PAParser())

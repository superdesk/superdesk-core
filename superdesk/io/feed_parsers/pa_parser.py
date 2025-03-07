from superdesk.io.feed_parsers.nitf import NITFFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.etree import etree
from superdesk.utc import utc
from datetime import datetime
import re


class PAParser(NITFFeedParser):
    """
    Feed Parser for PA (Press Association) XML files.
    """

    NAME = "pa_parser"
    label = "PA Parser"

    def can_parse(self, xml):
        """
        Check if the XML can be parsed by this parser.
        """
        return xml.tag == "document" and xml.find("nitf") is not None

    def parse(self, xml, provider=None):
        """
        Parse the XML and return a single dictionary representing the news item.
        """
        item = {}
        nitf = xml.find("nitf")
        if nitf is not None:
            self.parse_head(nitf, item)
            self.parse_body(nitf, item)
            self.parse_resource(xml, item)
        return item

    def parse_head(self, nitf, item):
        """
        Parse the head section of the NITF document.
        """
        head = nitf.find("head")
        if head is not None:
            title = head.find("title")
            if title is not None and title.text:
                item["headline"] = title.text

    def parse_body(self, nitf, item):
        """
        Parse the body section of the NITF document.
        """
        body = nitf.find("body")
        if body is not None:
            self.parse_body_head(body, item)
            self.parse_body_content(body, item)

    def parse_body_head(self, body, item):
        """
        Parse the body.head section of the NITF document.
        """
        body_head = body.find("body.head")
        if body_head is not None:
            self.parse_hedline(body_head, item)
            self.parse_byline(body_head, item)

    def parse_hedline(self, body_head, item):
        """
        Parse the hedline section of the NITF document.
        """
        hedline = body_head.find("hedline")
        if hedline is not None:
            hl1 = hedline.find("hl1")
            if hl1 is not None and hl1.text:
                item["headline"] = hl1.text

    def parse_byline(self, body_head, item):
        """
        Parse the byline section of the NITF document.
        """
        byline = body_head.find("byline")
        if byline is not None:
            bytag = byline.find("bytag")
            if bytag is not None and bytag.text:
                item["byline"] = bytag.text

    def parse_body_content(self, body, item):
        """
        Parse the body.content section of the NITF document and clean up HTML content.
        """
        body_content = body.find("body.content")
        if body_content is not None:
            body_html = etree.tostring(body_content, encoding="unicode", method="html")
            parser = etree.HTMLParser()
            tree = etree.fromstring(body_html, parser)
            etree.strip_tags(tree, "section", "body", "span", "body.content")
            cleaned_html = "".join(etree.tostring(child, encoding="unicode", method="html") for child in tree)
            item["body_html"] = cleaned_html

    def parse_resource(self, xml, item):
        """
        Parse the Resource section of the XML document.
        """
        resource = xml.find(".//xn:Resource", namespaces={"xn": "http://www.xmlnews.org/namespaces/meta#"})
        if resource is not None:
            for vendor_data in resource.findall(
                ".//xn:vendorData", namespaces={"xn": "http://www.xmlnews.org/namespaces/meta#"}
            ):
                if vendor_data.text and "PRESSUK_:Document ID=" in vendor_data.text:
                    document_id = vendor_data.text.split("PRESSUK_:Document ID=")[-1].strip()
                    if document_id:
                        item["guid"] = document_id
                        break
            self.parse_versioncreated(resource, item)
            self.parse_firstcreated(resource, item)
            self.parse_abstract(resource, item)
            self.parse_usageterms(resource, item)
            self.parse_word_count(resource, item)
            self.parse_keywords(resource, item)
            self.parse_embargo(resource, item)
            self.parse_priority(resource, item)

    def parse_versioncreated(self, resource, item):
        """
        Parse the versioncreated timestamp from the Resource section.
        """
        publication_time = resource.find(
            "xn:publicationTime", namespaces={"xn": "http://www.xmlnews.org/namespaces/meta#"}
        )
        if publication_time is not None and publication_time.text:
            item["versioncreated"] = datetime.strptime(publication_time.text, "%Y-%m-%dT%H:%M:%S+00:00").replace(
                tzinfo=utc
            )

    def parse_firstcreated(self, resource, item):
        """
        Parse the firstcreated timestamp from the Resource section.
        """
        received_time = resource.find("xn:receivedTime", namespaces={"xn": "http://www.xmlnews.org/namespaces/meta#"})
        if received_time is not None and received_time.text:
            item["firstcreated"] = datetime.strptime(received_time.text, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=utc)

    def parse_abstract(self, resource, item):
        """
        Parse the abstract from the Resource section.
        """
        description = resource.find("xn:description", namespaces={"xn": "http://www.xmlnews.org/namespaces/meta#"})
        if description is not None and description.text:
            item["abstract"] = description.text

    def parse_usageterms(self, resource, item):
        """
        Parse the usage terms (copyright) from the Resource section.
        """
        copyright = resource.find("xn:copyright", namespaces={"xn": "http://www.xmlnews.org/namespaces/meta#"})
        if copyright is not None and copyright.text:
            item["usageterms"] = copyright.text

    def parse_embargo(self, resource, item):
        """
        Parse the embargo timestamp from the Resource section.
        """
        for vendor_data in resource.findall("{http://www.xmlnews.org/namespaces/meta#}vendorData"):
            if vendor_data.text and "PRESSUK_:Expiration Date=" in vendor_data.text:
                embargo = vendor_data.text.split("PRESSUK_:Expiration Date=")[-1].strip()
                if embargo:
                    try:
                        embargo_dt = datetime.strptime(embargo, "%Y-%m-%dT%H:%M:%S%z")
                        item["embargo"] = embargo_dt.isoformat()
                    except ValueError:
                        pass

    def parse_word_count(self, resource, item):
        for vendor_data in resource.findall("{http://www.xmlnews.org/namespaces/meta#}vendorData"):
            if vendor_data.text and "PRESSUK_:Word Count=" in vendor_data.text:
                word_count = vendor_data.text.split("PRESSUK_:Word Count=")[-1].strip()
                if word_count:
                    try:
                        item["word_count"] = int(word_count)
                    except ValueError:
                        pass

    def parse_priority(self, resource, item):
        for vendor_data in resource.findall("{http://www.xmlnews.org/namespaces/meta#}vendorData"):
            if vendor_data.text and "PRESSUK_:PA Priority=" in vendor_data.text:
                priority = vendor_data.text.split("PRESSUK_:PA Priority=")[-1].strip()
                if priority:
                    try:
                        item["priority"] = int(priority)
                    except ValueError:
                        pass

    def parse_keywords(self, resource, item):
        keywords = []
        for vendor_data in resource.findall("{http://www.xmlnews.org/namespaces/meta#}vendorData"):
            if vendor_data.text and "PRESSUK_:Keyword=" in vendor_data.text:
                keyword = vendor_data.text.split("PRESSUK_:Keyword=")[-1].strip()
                if keyword:
                    keywords.append(keyword)
        if keywords:
            item["keywords"] = keywords


register_feed_parser(PAParser.NAME, PAParser())

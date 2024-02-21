# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import logging
import datetime

from copy import deepcopy
from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import FeedParser
from superdesk.utc import utc
from superdesk.metadata.utils import generate_tag_from_url
from typing import Optional, Dict, List, Any
from superdesk import get_resource_service
import collections

logger = logging.getLogger(__name__)


class NINJSFeedParser(FeedParser):
    """
    Feed Parser for NINJS format
    """

    NAME = "ninjs"

    label = "NINJS Feed Parser"

    direct_copy_properties = (
        "usageterms",
        "language",
        "headline",
        "copyrightnotice",
        "urgency",
        "pubstatus",
        "mimetype",
        "copyrightholder",
        "ednote",
        "body_text",
        "body_html",
        "slugline",
        "keywords",
        "extra",
        "byline",
        "description_text",
        "profile",
    )

    items = []

    def __init__(self):
        super().__init__()

    def can_parse(self, file_path):
        try:
            with open(file_path, "r") as f:
                ninjs = json.load(f)
                if ninjs.get("uri") or ninjs.get("guid"):
                    return True
        except Exception as err:
            logger.exception(err)
            logger.error("Failed to ingest json file")
            pass
        return False

    def parse(self, file_path, provider=None):
        self.items = []
        with open(file_path, "r") as f:
            ninjs = json.load(f)

        self.items.append(self._transform_from_ninjs(ninjs))
        return self.items

    def _transform_from_ninjs(self, ninjs):
        guid = ninjs.get("guid")
        if not guid and ninjs.get("uri"):
            guid = generate_tag_from_url(ninjs["uri"], "urn")
        item = {"guid": guid, "type": ninjs.get("type"), "uri": ninjs.get("uri")}

        for copy_property in self.direct_copy_properties:
            if ninjs.get(copy_property) is not None:
                item[copy_property] = ninjs[copy_property]

        if ninjs.get("source"):
            item["original_source"] = ninjs["source"]

        if ninjs.get("priority"):
            item["priority"] = int(ninjs["priority"])
        else:
            ninjs["priority"] = 5

        if ninjs.get("genre"):
            item["genre"] = self._format_qcodes(ninjs["genre"])

        if ninjs.get("service"):
            item["anpa_category"] = self._format_qcodes(ninjs["service"], "categories")

        if ninjs.get("subject"):
            item["subject"] = self._format_qcodes(ninjs["subject"])

        if ninjs.get("versioncreated"):
            item["versioncreated"] = self.datetime(ninjs.get("versioncreated"))

        if ninjs.get("firstcreated"):
            item["firstcreated"] = self.datetime(ninjs.get("firstcreated"))

        if ninjs.get("associations"):
            item["associations"] = {}

        for key, associated_item in ninjs.get("associations", {}).items():
            if associated_item:
                self.items.append(self._transform_from_ninjs(associated_item))
                if associated_item.get("type") == "picture" and associated_item.get("body_text"):
                    associated_item["alt_text"] = associated_item.get("body_text")
                if associated_item.get("versioncreated"):
                    associated_item["versioncreated"] = self.datetime(associated_item["versioncreated"])
                item["associations"][key] = deepcopy(associated_item)

        if ninjs.get("renditions"):
            item["renditions"] = self.parse_renditions(ninjs["renditions"])

        if ninjs.get("located"):
            item["dateline"] = {"located": {"city": ninjs.get("located")}}

        if ninjs.get("type") == "picture" and ninjs.get("body_text"):
            item["alt_text"] = ninjs.get("body_text")

        if ninjs.get("type") == "text" and ninjs.get("description_text"):
            item["abstract"] = ninjs.get("description_text")

        if ninjs.get("place"):
            item["place"] = self._format_qcodes(ninjs["place"])

        if ninjs.get("authors"):
            item["authors"] = self._parse_authors(ninjs["authors"])

        if not item.get("body_html") and ninjs.get("body_xhtml"):
            item["body_html"] = ninjs["body_xhtml"]

        if ninjs.get("embargoed"):
            item["embargoed"] = self.datetime(ninjs.get("embargoed"))

        return item

    def parse_renditions(self, renditions):
        rend = {}
        for rendition_name, rendition_data in renditions.items():
            parsed_rendition = {}

            # Parse href
            href = rendition_data.get("href", "")
            if isinstance(href, str) and href:
                parsed_rendition["href"] = href

            # Parse width and height
            width = rendition_data.get("width", None)
            height = rendition_data.get("height", None)
            if isinstance(width, int) and isinstance(height, int):
                parsed_rendition["width"] = width
                parsed_rendition["height"] = height

            # Parse mimetype
            mimetype = rendition_data.get("mimetype", "")
            if isinstance(mimetype, str) and mimetype:
                parsed_rendition["mimetype"] = mimetype

            # Parse poi
            poi = rendition_data.get("poi", {})
            if isinstance(poi, dict) and "x" in poi and "y" in poi:
                parsed_rendition["poi"] = {"x": poi["x"], "y": poi["y"]}

            # Parse media
            media = rendition_data.get("media", "")
            if isinstance(media, str) and media:
                parsed_rendition["media"] = media

            if parsed_rendition:
                rend[rendition_name] = parsed_rendition
        return rend

    def _format_qcodes(self, items: List[Dict[str, Any]], cv_name: Optional[str] = None) -> List[Dict[str, Any]]:
        subjects = []
        cv_items = collections.defaultdict(dict)
        cursor = get_resource_service("vocabularies").get_from_mongo(req=None, lookup={"_id": cv_name}) or {}
        for doc in cursor:
            cv_items.update({item["qcode"]: item for item in doc.get("items")})

        for item in items:
            if cv_items.get(item.get("code")):
                subject = cv_items[item["code"]]
            else:
                subject = {
                    "name": item.get("name"),
                    "qcode": item.get("code"),
                }
            if not subject.get("translations") and item.get("translations"):
                subject["translations"] = item["translations"]
            if not subject.get("scheme") and item.get("scheme"):
                subject["scheme"] = item["scheme"]
            subjects.append(subject)

        return subjects

    def datetime(self, string):
        try:
            return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S+0000").replace(tzinfo=utc)
        except ValueError:
            try:
                return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc)
            except ValueError:
                return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=utc)

    def _parse_authors(self, authors):
        return [self._parse_author(author) for author in authors]

    def _parse_author(self, author):
        parsed = {
            "name": author["name"],
            "role": author.get("role", ""),
        }

        if author.get("avatar_url"):
            parsed["avatar_url"] = author["avatar_url"]

        if author.get("biography"):
            parsed["biography"] = author["biography"]

        return parsed


register_feed_parser(NINJSFeedParser.NAME, NINJSFeedParser())

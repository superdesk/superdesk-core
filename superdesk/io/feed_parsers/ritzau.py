# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE
from superdesk.errors import ParserError
from superdesk import etree as sd_etree
from collections import OrderedDict
from superdesk import text_utils
from superdesk.utc import local_to_utc
import superdesk
import dateutil.parser
import logging

logger = logging.getLogger(__name__)
NS = {"r": "http://tempuri.org/", "a": "http://schemas.microsoft.com/2003/10/Serialization/Arrays"}


class RitzauFeedParser(XMLFeedParser):
    """
    Feed Parser which can parse Ritzau XML feed
    """

    _subjects_map = None

    NAME = "ritzau"
    label = "Ritzau feed"
    TIMEZONE = "Europe/Copenhagen"

    def __init__(self):
        super().__init__()

        self.default_mapping = OrderedDict(
            [
                ("guid", "NewsID/text()"),
                ("body_html", {"xpath": "content/text()", "filter": sd_etree.clean_html_str}),
                (
                    "firstcreated",
                    {
                        "xpath": "PublishDate/text()",
                        "filter": self._publish_date_filter,
                    },
                ),
                (
                    "versioncreated",
                    {
                        "xpath": "PublishDate/text()",
                        "filter": self._publish_date_filter,
                    },
                ),
                ("headline", {"xpath": "headline/text()", "default": "", "key_hook": self._set_headline}),
                ("priority", {"xpath": "Priority/text()", "filter": int}),
                ("urgency", {"xpath": "Priority/text()", "filter": int}),
                ("keywords", {"xpath": "strapline/text()", "filter": lambda v: list(filter(None, v.split("/")))}),
                ("abstract", "subtitle"),
                ("byline", "origin"),
                ("version", {"xpath": "version/text()", "filter": int}),
                ("ednote", {"xpath": "TilRedaktionen/text()", "filter": self._ednote_filter}),
                ("subject", {"xpath": "IPTCList/a:int/text()", "list": True, "filter": self._subject_filter}),
            ]
        )

    @property
    def subjects_map(self):
        if self._subjects_map is None:
            voc_subjects = superdesk.get_resource_service("vocabularies").find_one(req=None, _id="subject_custom")
            if voc_subjects is not None:
                self._subjects_map = {i["qcode"]: i for i in voc_subjects["items"]}
            else:
                self._subjects_map = {}
        return self._subjects_map

    def can_parse(self, xml):
        return xml.tag.endswith("RBNews")

    def parse(self, xml, provider=None):
        item = {
            ITEM_TYPE: CONTENT_TYPE.TEXT,  # set the default type.
        }
        try:
            self.do_mapping(item, xml, namespaces=NS)
        except Exception as ex:
            raise ParserError.parseMessageError(ex, provider)
        return item

    def get_datetime(self, value):
        return dateutil.parser.parse(value)

    def _subject_filter(self, qcode):
        try:
            subject = self.subjects_map[qcode]
        except KeyError:
            return None
        else:
            if not subject.get("is_active", False):
                return None
            name = subject.get("name", "")

        return {"qcode": qcode, "name": name, "scheme": "subject_custom"}

    def _publish_date_filter(self, date_string):
        local = dateutil.parser.parse(date_string)
        return local_to_utc(self.TIMEZONE, local)

    def _set_headline(self, item, value):
        if not value:
            # if there is no headline, we use first 100 chars of body
            # cf. SDNTB-481
            value = text_utils.get_text(item.get("body_html", ""), "html")[:100]
        item["headline"] = value

    def _ednote_filter(self, ednote):
        return text_utils.get_text(ednote, lf_on_block=True).strip()


register_feed_parser(RitzauFeedParser.NAME, RitzauFeedParser())

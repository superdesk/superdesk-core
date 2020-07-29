# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from os.path import join
import logging
import requests
from superdesk import get_resource_service
from superdesk import etree
from superdesk.errors import SuperdeskApiError
from .base import AIServiceBase

logger = logging.getLogger(__name__)
TIMEOUT = 30

# iMatrics concept type to SD type mapping
CONCEPT_MAPPING = {
    "topic": "subject",
    "category": "subject",
    "organisation": "organisation",
    "Name LastName": "person",
    "place": "place",
}


class IMatrics(AIServiceBase):
    """IMatrics autotagging service

    The IMATRICS_BASE_URL, IMATRICS_USER and IMATRICS_KEY setting (or environment variable) must be set
    """

    name = "imatrics"
    label = "IMatrics autotagging service"

    def __init__(self, app):
        super().__init__(app)
        self.base_url = self.config.get("IMATRICS_BASE_URL", os.environ.get("IMATRICS_BASE_URL"))
        self.user = self.config.get("IMATRICS_USER", os.environ.get("IMATRICS_USER"))
        self.key = self.config.get("IMATRICS_KEY", os.environ.get("IMATRICS_KEY"))

    def analyze(self, item_id: str) -> dict:
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured propertly, can't analyze article")
            return {}
        url = join(self.base_url, "article/concept")
        archive_service = get_resource_service("archive")
        item = archive_service.find_one(req=None, _id=item_id)
        if item is None:
            logger.warning("Could not find any item with id {item_id}".format(item_id=item_id))
            return {}

        try:
            body = [p.strip() for p in item["body_text"].split("\n") if p.strip()]
        except KeyError:
            body = [
                p.strip() for p in etree.to_string(etree.parse_html(item["body_html"]), method="text").split("\n")
                if p.strip()
            ]

        data = {
            "uuid": item["guid"],
            "headline": item["headline"],
            "body": body,
        }
        r = requests.post(url, json=data, auth=(self.user, self.key), timeout=TIMEOUT)
        if r.status_code != 200:
            raise SuperdeskApiError.internalError("Unexpected return code from {}".format(self.name))

        data = r.json()

        analyzed_data = {}

        for concept in data:
            try:
                tag_type = CONCEPT_MAPPING[concept["type"]]
            except KeyError:
                logger.warning("no mapping for concept type {concept_type!r}".format(concept_type=concept["type"]))
                tag_type = concept["type"]
            tag_data = {
                "uuid": concept["uuid"],
                "title": concept["title"],
                "weight": concept["weight"],
            }
            if tag_type == "Name LastName":
                title = tag_data.pop("title")
                try:
                    tag_data["firstname"], tag_data["lastname"] = title.split(" ", 1)
                except ValueError:
                    tag_data["firstname"], tag_data["lastname"] = "", title

            media_topics = tag_data["media_topics"] = []
            for link in concept.get('links', []):
                if link.get("source") == "IPTC":
                    topic_id = link.get("id", "")
                    if topic_id.startswith("medtop:"):
                        topic_id = topic_id[7:]
                    media_topics.append({
                        "name": concept["title"],
                        "code": topic_id,
                    })
                else:
                    tag_data.setdefault('links', []).append(link)

            analyzed_data.setdefault(tag_type, []).append(tag_data)

        for tags in analyzed_data.values():
            tags.sort(key=lambda d: d["weight"], reverse=True)
            for tag in tags:
                del tag["weight"]

        return analyzed_data

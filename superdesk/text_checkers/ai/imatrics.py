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
from collections import OrderedDict
from typing import Optional
from superdesk import get_resource_service
from superdesk import etree
from superdesk.errors import SuperdeskApiError
from .base import AIServiceBase

logger = logging.getLogger(__name__)
TIMEOUT = 30

# iMatrics concept type to SD type mapping
CONCEPT_MAPPING = OrderedDict([
    # following concepts don't have clear equivalent in SD
    ("category", "subject"),
    ("object", "subject"),
    ("entity", "organisation"),
    ("event", "subject"),

    ("topic", "subject"),
    ("organisation", "organisation"),
    ("Name LastName", "person"),
    # both Name LastName and person are seens in iMatrics examples and docs
    ("person", "person"),
    ("place", "place"),
])

DEFAULT_CONCEPT_TYPE = "topic"


class IMatrics(AIServiceBase):
    """IMatrics autotagging service

    The IMATRICS_BASE_URL, IMATRICS_USER and IMATRICS_KEY setting (or environment variable) must be set
    IMATRICS_AUTHOR can be used to set ``author`` of concept (which translates to ``source`` in Superdesk)
    """

    name = "imatrics"
    label = "IMatrics autotagging service"

    def __init__(self, app):
        super().__init__(app)
        self.base_url = self.config.get("IMATRICS_BASE_URL", os.environ.get("IMATRICS_BASE_URL"))
        self.user = self.config.get("IMATRICS_USER", os.environ.get("IMATRICS_USER"))
        self.key = self.config.get("IMATRICS_KEY", os.environ.get("IMATRICS_KEY"))
        self.convept_map_inv = {v: k for k, v in CONCEPT_MAPPING.items()}

    def concept2tag_data(self, concept: dict) -> dict:
        """Convert an iMatrics concept to Superdesk friendly data"""
        tag_data = {
            "uuid": concept["uuid"],
            "title": concept["title"],
        }
        try:
            tag_type = CONCEPT_MAPPING[concept["type"]]
        except KeyError:
            logger.warning("no mapping for concept type {concept_type!r}".format(concept_type=concept["type"]))
            tag_type = concept["type"]

        if "author" in concept:
            tag_data["source"] = concept["author"]

        tag_data["type"] = tag_type

        try:
            tag_data["weight"] = concept["weight"]
        except KeyError:
            pass
        if tag_type == "person":
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

        return tag_data

    def check_verb(self, expected: str, verb: str, operation: str) -> None:
        """Check that HTTP verb use is the one expected for this operation"""
        if verb != expected:
            raise SuperdeskApiError.badRequestError(
                "[{name}] Unexpected verb for {operation}: {verb}".format(
                    name=self.name, verb=verb, operation=operation)
            )

    def analyze(self, item_id: str) -> dict:
        """Analyze article to get tagging suggestions"""
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
            raise SuperdeskApiError.proxyError("Unexpected return code ({status_code}) from {name}: {msg}".format(
                name=self.name,
                status_code=r.status_code,
                msg=r.text,
            ))

        r_data = r.json()

        analyzed_data = {}

        for concept in r_data:
            tag_data = self.concept2tag_data(concept)
            tag_type = tag_data.pop("type")
            analyzed_data.setdefault(tag_type, []).append(tag_data)

        for tags in analyzed_data.values():
            tags.sort(key=lambda d: d["weight"], reverse=True)
            for tag in tags:
                del tag["weight"]

        return analyzed_data

    def search(self, data: dict) -> dict:
        search_url = join(self.base_url, "concept/get")

        data = {
            "title": data['term'],
            "type": "all",
            "draft": False,
            "size": 10,
        }
        r = requests.post(
            search_url,
            params={'operation': 'title_type'},
            json=data,
            auth=(self.user, self.key),
            timeout=TIMEOUT
        )

        if r.status_code != 200:
            raise SuperdeskApiError.proxyError("Unexpected return code ({status_code}) from {name}: {msg}".format(
                name=self.name,
                status_code=r.status_code,
                msg=r.text,
            ))

        r_data = r.json()

        tags = []
        ret = {
            'tags': tags
        }
        for concept in r_data['result']:
            tag_data = self.concept2tag_data(concept)
            tags.append(tag_data)

        return ret

    def create(self, data: dict) -> dict:
        create_url = join(self.base_url, "concept/create")
        concept = {}

        try:
            concept["title"] = data["title"]
        except KeyError:
            raise SuperdeskApiError.badRequestError(
                "[{name}] missing title when creating tag: {data}".format(
                    name=self.name, data=data)
            )

        sd_type = data.get("type", "subject")
        try:
            concept["type"] = self.convept_map_inv[sd_type]
        except KeyError:
            logger.warning("no mapping for superdesk type {sd_type!r}".format(sd_type=sd_type))
            concept["type"] = "topic"

        r = requests.post(
            create_url,
            json=concept,
            auth=(self.user, self.key),
            timeout=TIMEOUT
        )

        if r.status_code != 200:
            raise SuperdeskApiError.proxyError("Unexpected return code ({status_code}) from {name}: {msg}".format(
                name=self.name,
                status_code=r.status_code,
                msg=r.text,
            ))

        r_data = r.json()

        if r_data['error']:
            raise SuperdeskApiError.proxyError(
                "iMatrics concept creation failed: {msg}".format(msg=r_data.get("response", ""))
            )

        return {}

    def delete(self, data: dict) -> dict:
        try:
            uuid = data["uuid"].strip()
            if not uuid:
                raise KeyError
        except KeyError:
            raise SuperdeskApiError.badRequestError("[{name}] no tag UUID specified".format(name=self.name))

        delete_url = join(self.base_url, "concept/delete")
        r = requests.delete(
            delete_url,
            params={'uuid': data["uuid"]},
            auth=(self.user, self.key),
            timeout=TIMEOUT
        )

        if r.status_code != 200:
            raise SuperdeskApiError.proxyError("Unexpected return code ({status_code}) from {name}: {msg}".format(
                name=self.name,
                status_code=r.status_code,
                msg=r.text,
            ))

        return {}

    def data_operation(
        self,
        verb: str,
        operation: str,
        name: Optional[str],
        data: dict
    ) -> dict:
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured propertly, can't analyze article")
            return {}
        if operation == 'search':
            self.check_verb("POST", verb, operation)
            return self.search(data)
        elif operation == 'create':
            self.check_verb("POST", verb, operation)
            return self.create(data)
        elif operation == 'delete':
            self.check_verb("POST", verb, operation)
            return self.delete(data)
        else:
            raise SuperdeskApiError.badRequestError(
                "[{name}] Unexpected operation: {operation}".format(
                    name=name, operation=operation)
            )

# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import logging
import requests
import superdesk

from flask import current_app
from collections import OrderedDict
from typing import Optional, Dict, List, Set
from urllib.parse import urljoin
from superdesk.text_utils import get_text
from superdesk.errors import SuperdeskApiError
from .base import AIServiceBase

logger = logging.getLogger(__name__)
TIMEOUT = 30

# iMatrics concept type to SD type mapping
CONCEPT_MAPPING = OrderedDict(
    [
        # following concepts don't have clear equivalent in SD
        ("category", "subject"),
        ("object", "object"),
        ("entity", "organisation"),
        ("event", "event"),
        ("topic", "subject"),
        ("organisation", "organisation"),
        ("Name LastName", "person"),
        # both Name LastName and person are seens in iMatrics examples and docs
        ("person", "person"),
        ("place", "place"),
    ]
)

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
        self.convept_map_inv = {v: k for k, v in CONCEPT_MAPPING.items()}
        self._subjects = []

    @property
    def base_url(self):
        return current_app.config.get("IMATRICS_BASE_URL", os.environ.get("IMATRICS_BASE_URL"))

    @property
    def user(self):
        return current_app.config.get("IMATRICS_USER", os.environ.get("IMATRICS_USER"))

    @property
    def key(self):
        return current_app.config.get("IMATRICS_KEY", os.environ.get("IMATRICS_KEY"))

    def concept2tag_data(self, concept: dict) -> dict:
        """Convert an iMatrics concept to Superdesk friendly data"""
        tag_data = {
            "name": concept["title"],
            "qcode": concept["uuid"],
            "parent": concept.get("broader") or None,
            "source": "imatrics",
            "aliases": concept.get("aliases", []),
            "original_source": concept.get("source"),
            "altids": {
                "imatrics": concept["uuid"],
            },
        }

        if concept.get("shortDescription") and concept["shortDescription"].strip() != "NaN":
            tag_data["description"] = concept["shortDescription"].strip()

        try:
            tag_type = CONCEPT_MAPPING[concept["type"]]
        except KeyError:
            logger.warning("no mapping for concept type {concept_type!r}".format(concept_type=concept["type"]))
            tag_type = concept["type"]

        tag_data["type"] = tag_type

        try:
            tag_data["weight"] = concept["weight"]
        except KeyError:
            pass

        for link in concept.get("links", []):
            if link.get("source") == "IPTC":
                topic_id = link.get("id", "")
                if topic_id.startswith("medtop:"):
                    topic_id = topic_id[7:]
                    subject = self.find_subject(topic_id)
                    if subject:
                        tag_data.update(subject)
                    tag_data["altids"]["medtop"] = topic_id

        if concept["type"] in ("topic", "category"):
            tag_data.setdefault("scheme", "imatrics_{}".format(concept["type"]))

        return tag_data

    def find_subject(self, topic_id):
        SCHEME_ID = current_app.config.get("IMATRICS_SUBJECT_SCHEME")
        if not SCHEME_ID:
            return
        if not self._subjects:
            cv = superdesk.get_resource_service("vocabularies").find_one(req=None, _id=SCHEME_ID)
            if cv and cv.get("items"):
                self._subjects = [item for item in cv["items"] if item.get("is_active")]
        for subject in self._subjects:
            if subject.get("qcode") == topic_id:
                return superdesk.get_resource_service("vocabularies").get_article_cv_item(subject, SCHEME_ID)

    def check_verb(self, expected: str, verb: str, operation: str) -> None:
        """Check that HTTP verb use is the one expected for this operation"""
        if verb != expected:
            raise SuperdeskApiError.badRequestError(
                "[{name}] Unexpected verb for {operation}: {verb}".format(
                    name=self.name, verb=verb, operation=operation
                )
            )

    def _parse_concepts(
        self, analyzed_data: Dict[str, List], concepts: List[dict], seen_qcodes: set, new_concepts_to_get: set
    ) -> None:
        """Parse response data, convert iMatrics concepts to SD data and add them to analyzed_data"""
        for concept in concepts:
            tag_data = self.concept2tag_data(concept)
            seen_qcodes.add(tag_data["qcode"])
            parent = tag_data["parent"]
            if parent is not None and parent not in seen_qcodes:
                new_concepts_to_get.add(parent)
            tag_type = tag_data.pop("type")
            analyzed_data.setdefault(tag_type, []).append(tag_data)

    def analyze(self, item: dict) -> dict:
        """Analyze article to get tagging suggestions"""
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured propertly, can't analyze article")
            return {}
        body = get_item_body(item)
        headline = item.get("headline", "")
        if not body and not headline:
            logger.warning("no body nor headline found in item {item_id!r}".format(item_id=item["guid"]))
            # we return an empty result
            return {"subject": []}

        data = {
            "uuid": item["guid"],
            "pubStatus": False,
            "headline": headline,
            "body": body,
            "language": item["language"],
        }

        r_data = self._request(
            "article/analysis",
            data,
            params=dict(conceptFields="uuid,title,type,shortDescription,aliases,source,weight,broader"),
        )

        analyzed_data: Dict[str, List] = {}

        seen_qcodes: Set[str] = set()
        new_concepts_to_get: Set[str] = set()
        self._parse_concepts(analyzed_data, r_data["concepts"], seen_qcodes, new_concepts_to_get)
        while new_concepts_to_get:
            to_get = new_concepts_to_get.copy()
            new_concepts_to_get.clear()
            for concept_id in to_get:
                r_data = self._request("concept/get", {"uuid": concept_id}, params=dict(operation="id"))
                self._parse_concepts(analyzed_data, r_data["result"], seen_qcodes, new_concepts_to_get)

        for tags in analyzed_data.values():
            tags.sort(key=lambda d: d.get("weight", 0), reverse=True)
            for tag in tags:
                try:
                    del tag["weight"]
                except KeyError:
                    pass

        return analyzed_data

    def search(self, data: dict) -> dict:

        data = {
            "title": data["term"],
            "type": "all",
            "draft": False,
            "size": 10,
        }

        r_data = self._request("concept/get", data, params=dict(operation="title_type"))

        tags: Dict[str, List[Dict]] = {}
        ret = {"tags": tags}
        for concept in r_data["result"]:
            tag_data = self.concept2tag_data(concept)
            tag_type = tag_data.pop("type")
            tags.setdefault(tag_type, []).append(tag_data)

        return ret

    def create(self, data: dict) -> dict:
        concept = {}

        try:
            concept["title"] = data["title"]
        except KeyError:
            raise SuperdeskApiError.badRequestError(
                "[{name}] missing title when creating tag: {data}".format(name=self.name, data=data)
            )

        sd_type = data.get("type", "subject")
        try:
            concept["type"] = self.convept_map_inv[sd_type]
        except KeyError:
            logger.warning("no mapping for superdesk type {sd_type!r}".format(sd_type=sd_type))
            concept["type"] = "topic"

        r_data = self._request("concept/create", concept)

        if r_data["error"]:
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

        self._request("concept/delete", method="DELETE", params={"uuid": data["uuid"]})
        return {}

    def data_operation(self, verb: str, operation: str, name: Optional[str], data: dict) -> dict:
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured propertly, can't analyze article")
            return {}
        if operation == "search":
            self.check_verb("POST", verb, operation)
            return self.search(data)
        elif operation == "create":
            self.check_verb("POST", verb, operation)
            return self.create(data)
        elif operation == "delete":
            self.check_verb("POST", verb, operation)
            return self.delete(data)
        else:
            raise SuperdeskApiError.badRequestError(
                "[{name}] Unexpected operation: {operation}".format(name=name, operation=operation)
            )

    def publish(self, data):
        return self._request("article/concept", data)

    def _request(self, service, data=None, method="POST", params=None):
        url = urljoin(self.base_url, service)
        r = requests.request(method, url, json=data, auth=(self.user, self.key), params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            raise SuperdeskApiError.proxyError(
                "Unexpected return code ({status_code}) from {name}: {msg}".format(
                    name=self.name,
                    status_code=r.status_code,
                    msg=r.text,
                )
            )
        return r.json()


def get_item_body(item):
    body = []
    for field in ("body_html", "abstract"):
        try:
            body.extend([p.strip() for p in get_text(item[field], "html", True).split("\n") if p.strip()])
        except KeyError:
            pass
    return body

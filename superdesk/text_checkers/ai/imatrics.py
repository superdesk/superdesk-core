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

from flask import current_app, json
from collections import OrderedDict
from typing import Optional, Dict, List, Tuple
from urllib.parse import urljoin
from superdesk.default_settings import SCHEMA
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

SCHEME_MAPPING = {
    "category": "mediatopic",
    "topic": "imatrics_topic",
}

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

    def concept2tag_data(self, concept: dict) -> Tuple[dict, str]:
        """Convert an iMatrics concept to Superdesk friendly data"""
        tag_data = {
            "name": concept["title"],
            "qcode": concept["uuid"],
            "parent": concept.get("broader") or None,
            "source": "imatrics",
            "aliases": concept.get("aliases", []),
            "original_source": concept.get("author") or concept.get("source"),
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

        try:
            tag_data["weight"] = concept["weight"]
        except KeyError:
            pass

        for link in concept.get("links", []):
            if link.get("source").lower() == "iptc" and link.get("relationType") == "exactMatch" and link.get("id"):
                topic_id = link["id"]
                if topic_id.startswith("medtop:"):
                    topic_id = topic_id[7:]
                subject = self.find_subject(topic_id)
                if subject:
                    tag_data.update(subject)
                tag_data["altids"]["medtop"] = topic_id
            elif (
                link.get("source").lower() == "wikidata"
                and link.get("relationType") in ("exactMatch", "linked")
                and link.get("id")
            ):
                tag_data["altids"]["wikidata"] = link["id"]

        if concept["type"] in SCHEME_MAPPING:
            tag_data.setdefault("scheme", SCHEME_MAPPING[concept["type"]])

        return tag_data, tag_type

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

    def _parse_concepts(self, concepts: List[dict]) -> Dict[str, List]:
        """Parse response data, convert iMatrics concepts to SD data and add them to analyzed_data"""
        analyzed_data: Dict[str, List] = {}
        for concept in concepts:
            tag_data, tag_type = self.concept2tag_data(concept)
            analyzed_data.setdefault(tag_type, []).append(tag_data)
        for tags in analyzed_data.values():
            tags.sort(key=lambda d: d.get("weight", 0), reverse=True)
            for tag in tags:
                try:
                    del tag["weight"]
                except KeyError:
                    pass
        return analyzed_data

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

        r_data = self._analyze(data)
        return self._parse_concepts(r_data["concepts"] + r_data["broader"])

    def _analyze(self, data, **params):
        return self._request(
            "article/analysis",
            data,
            params=dict(
                conceptFields="uuid,title,type,shortDescription,aliases,source,author,weight,broader,links",
                **params,
            ),
        )

    def search2(self, reg: dict) -> dict:
        """Test search via analyze, it's missing entities."""
        data = {
            "body": [],
            "headline": reg["term"],
            "pubStatus": False,
            "language": reg["language"],
        }

        test_data = self._analyze(data, cleanText=False, categories=10, entities=10)
        tags = self._parse_concepts(test_data["concepts"])
        broader = self._parse_concepts(test_data["broader"])
        return {"tags": tags, "broader": broader}

    def search(self, reg: dict) -> dict:
        data = {
            "title": reg["term"],
            "type": "all",
            "draft": False,
            "size": 10,
        }

        r_data = self._request(
            "concept/get",
            data,
            params=dict(
                operation="title_type",
                conceptFields="uuid,title,type,shortDescription,aliases,source,author,weight,broader",
            ),
        )

        tags: Dict[str, List[Dict]] = {}
        broader: Dict[str, List[Dict]] = {}
        for concept in r_data["result"]:
            tag_data, tag_type = self.concept2tag_data(concept)
            tags.setdefault(tag_type, []).append(tag_data)
            if tag_type == "subject":
                broader.setdefault(tag_type, [])
                self._fetch_parent(broader[tag_type], concept)
        return dict(tags=tags, broader=broader)

    def _fetch_parent(self, broader, concept):
        parent_id = concept.get("broader")
        if not parent_id:
            return
        parent = self._get_parent(parent_id)
        if not parent:
            return
        tag_data, _ = self.concept2tag_data(parent)
        if tag_data["qcode"] in [b["qcode"] for b in broader]:
            return
        broader.append(tag_data)
        self._fetch_parent(broader, parent)

    def _get_parent(self, parent_id: str):
        data = {"uuid": parent_id}
        return self._request(
            "concept/get",
            data,
            params=dict(
                operation="id",
                conceptFields="uuid,title,type,shortDescription,aliases,source,weight,broader",
            ),
        )["result"][0]

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

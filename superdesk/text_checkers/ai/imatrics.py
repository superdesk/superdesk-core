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

from flask import current_app
from collections import OrderedDict
from typing import Optional, Dict, List
from urllib.parse import urljoin
from superdesk import etree
from superdesk.errors import SuperdeskApiError
from .base import AIServiceBase

logger = logging.getLogger(__name__)
TIMEOUT = 30

# iMatrics concept type to SD type mapping
CONCEPT_MAPPING = OrderedDict([
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
        self.convept_map_inv = {v: k for k, v in CONCEPT_MAPPING.items()}

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
            "source": "imatrics",
            "altids": {
                "imatrics": concept["uuid"],
            }
        }

        if concept.get("shortDescription") and concept["shortDescription"].strip():
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

        for link in concept.get('links', []):
            if link.get("source") == "IPTC":
                topic_id = link.get("id", "")
                if topic_id.startswith("medtop:"):
                    topic_id = topic_id[7:]
                    tag_data["qcode"] = topic_id
                    tag_data["altids"]["medtop"] = topic_id

        if concept["type"] in ('topic', 'category'):
            tag_data['scheme'] = 'imatrics_{}'.format(concept["type"])

        return tag_data

    def check_verb(self, expected: str, verb: str, operation: str) -> None:
        """Check that HTTP verb use is the one expected for this operation"""
        if verb != expected:
            raise SuperdeskApiError.badRequestError(
                "[{name}] Unexpected verb for {operation}: {verb}".format(
                    name=self.name, verb=verb, operation=operation)
            )

    def analyze(self, item: dict) -> dict:
        """Analyze article to get tagging suggestions"""
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured propertly, can't analyze article")
            return {}
        try:
            body = [p.strip() for p in item["body_text"].split("\n") if p.strip()]
        except KeyError:
            try:
                body = [
                    p.strip() for p in etree.to_string(etree.parse_html(item["body_html"]), method="text").split("\n")
                    if p.strip()
                ]
            except KeyError:
                logger.warning("no body found in item {item_id!r}".format(item_id=item['guid']))
                body = []

        headline = item.get('headline', '')
        if not body and not headline:
            logger.warning("no body nor headline found in item {item_id!r}".format(item_id=item['guid']))
            # we return an empty result
            return {"subject": []}

        data = {
            "uuid": item["guid"],
            "headline": headline,
            "body": body,
        }

        r_data = self._request("article/concept", data)

        analyzed_data: Dict[str, List] = {}

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

        data = {
            "title": data['term'],
            "type": "all",
            "draft": False,
            "size": 10,
        }

        r_data = self._request("concept/get", data, params=dict(operation='title_type'))

        tags: Dict[str, List[Dict]] = {}
        ret = {'tags': tags}
        for concept in r_data['result']:
            tag_data = self.concept2tag_data(concept)
            tag_type = tag_data.pop('type')
            tags.setdefault(tag_type, []).append(tag_data)

        return ret

    def create(self, data: dict) -> dict:
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

        r_data = self._request("concept/create", concept)

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

        self._request("concept/delete", method='DELETE', params={'uuid': data["uuid"]})
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

    def publish(self, data):
        return self._request('article/publish', data)

    def _request(self, service, data=None, method='POST', params=None):
        url = urljoin(self.base_url, service)
        r = requests.request(method, url, json=data, auth=(self.user, self.key), params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            raise SuperdeskApiError.proxyError("Unexpected return code ({status_code}) from {name}: {msg}".format(
                name=self.name,
                status_code=r.status_code,
                msg=r.text,
            ))
        return r.json()

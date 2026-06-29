# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Optional, Dict, List, Tuple
import os
import logging
from collections import OrderedDict
from urllib.parse import urljoin

from quart_babel import gettext as _
import aiohttp

import superdesk
from superdesk.core import get_config
from superdesk.core.web import AsyncHttpClientSessionMixin
from superdesk.text_utils import get_text
from superdesk.errors import SuperdeskApiError
from .base import AIServiceBase

logger = logging.getLogger(__name__)

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
    "place": "place_custom",
}

DEFAULT_CONCEPT_TYPE = "topic"


class IMatrics(AIServiceBase, AsyncHttpClientSessionMixin):
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
        self._places = None

    @property
    def base_url(self):
        return get_config(str, "IMATRICS_BASE_URL", os.environ.get("IMATRICS_BASE_URL"))

    @property
    def user(self):
        return get_config(str, "IMATRICS_USER", os.environ.get("IMATRICS_USER"))

    @property
    def key(self):
        return get_config(str, "IMATRICS_KEY", os.environ.get("IMATRICS_KEY"))

    @property
    def auth_header(self) -> aiohttp.BasicAuth | None:
        user, key = self.user, self.key
        if user and key:
            return aiohttp.BasicAuth(user, key)
        return None

    @property
    def image_base_url(self):
        return get_config(str, "IMATRICS_IMAGE_BASE_URL", os.environ.get("IMATRICS_IMAGE_BASE_URL"))

    @property
    def image_key(self):
        return get_config(str, "IMATRICS_IMAGE_KEY", os.environ.get("IMATRICS_IMAGE_KEY"))

    async def concept2tag_data(self, concept: dict) -> Tuple[dict, str]:
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
                subject = await self.find_subject(topic_id)
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

        if tag_type == "place":
            await self.sync_place(tag_data)

        return tag_data, tag_type

    async def find_subject(self, topic_id) -> dict | None:
        SCHEME_ID = get_config(str, "IMATRICS_SUBJECT_SCHEME", None)
        if not SCHEME_ID:
            return None
        if not self._subjects:
            cv = await superdesk.get_resource_service("vocabularies").find_one_async(req=None, _id=SCHEME_ID)
            if cv and cv.get("items"):
                self._subjects = [item for item in cv["items"] if item.get("is_active")]
        for subject in self._subjects:
            if subject.get("qcode") == topic_id:
                return superdesk.get_resource_service("vocabularies").get_article_cv_item(subject, SCHEME_ID)

        return None

    async def sync_place(self, place_data):
        if self._places is None:
            places = await superdesk.get_resource_service("vocabularies").get_items_async(SCHEME_MAPPING["place"])
            self._places = {p["qcode"]: p for p in places}
        place = self._places.get(place_data["qcode"])
        if place:
            place_data.update(place)

    def check_verb(self, expected: str, verb: str, operation: str) -> None:
        """Check that HTTP verb use is the one expected for this operation"""
        if verb != expected:
            raise SuperdeskApiError.badRequestError(
                "[{name}] Unexpected verb for {operation}: {verb}".format(
                    name=self.name, verb=verb, operation=operation
                )
            )

    async def _parse_concepts(self, concepts: List[dict]) -> Dict[str, List]:
        """Parse response data, convert iMatrics concepts to SD data and add them to analyzed_data"""
        analyzed_data: Dict[str, List] = {}
        for concept in concepts:
            tag_data, tag_type = await self.concept2tag_data(concept)
            analyzed_data.setdefault(tag_type, []).append(tag_data)
        for tags in analyzed_data.values():
            tags.sort(key=lambda d: d.get("weight", 0), reverse=True)
            for tag in tags:
                try:
                    del tag["weight"]
                except KeyError:
                    pass
        return analyzed_data

    def _transform_to_imatrics(self, item, publish=False):
        body = get_item_body(item)
        headline = item.get("headline", "")
        return {
            "uuid": item["guid"],
            "pubStatus": publish,
            "headline": headline,
            "body": body,
            "language": item["language"],
        }

    async def analyze(self, item: dict, tags: Optional[dict] = None) -> dict:
        """Analyze article to get tagging suggestions"""
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured propertly, can't analyze article")
            return {}
        data = self._transform_to_imatrics(item)
        if tags is not None:
            data["concepts"] = self._format_concepts(tags)
        if not data.get("headline") and not data.get("body"):
            logger.warning("no body nor headline found in item {item_id!r}".format(item_id=item["guid"]))
            # we return an empty result
            return {"subject": []}
        r_data = await self._analyze(data)
        return await self._parse_concepts(r_data["concepts"] + r_data["broader"])

    async def _analyze(self, data: dict, **params) -> dict:
        return await self._request(
            "article/analysis",
            data,
            params=dict(
                conceptFields="uuid,title,type,shortDescription,aliases,source,author,weight,broader,links",
                **params,
            ),
        )

    async def search_images(self, items: list) -> list:
        """Fetch image suggestions"""
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured properly, can't fetch images")
            return []
        data = items
        try:
            r_data = await self._search_images(data)
        except Exception as err:
            logger.exception(err)
            return []
        return [image for image in r_data if isinstance(image["imageUrl"], str) and image["imageUrl"] != ""]

    async def _search_images(self, data: list[dict], **params) -> list[dict]:
        return await self._request_images(
            "images/search",
            data,
            params=dict(**params),
        )

    async def search2(self, reg: dict) -> dict:
        """Test search via analyze, it's missing entities."""
        data = {
            "body": [],
            "headline": reg["term"],
            "pubStatus": False,
            "language": reg["language"],
        }

        test_data = await self._analyze(data, cleanText=False, categories=10, entities=10)
        tags = await self._parse_concepts(test_data["concepts"])
        broader = await self._parse_concepts(test_data["broader"])
        return {"tags": tags, "broader": broader}

    async def search(self, reg: dict) -> dict:
        data = {
            "title": reg["term"],
            "type": "all",
            "draft": False,
            "size": 10,
        }

        r_data = await self._request(
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
            tag_data, tag_type = await self.concept2tag_data(concept)
            tags.setdefault(tag_type, []).append(tag_data)
            if tag_type == "subject":
                broader.setdefault(tag_type, [])
                await self._fetch_parent(broader[tag_type], concept)
        return dict(tags=tags, broader=broader)

    async def _fetch_parent(self, broader, concept):
        parent_id = concept.get("broader")
        if not parent_id:
            return
        parent = await self._get_parent(parent_id)
        if not parent:
            return
        tag_data, _ = await self.concept2tag_data(parent)
        if tag_data["qcode"] in [b["qcode"] for b in broader]:
            return
        broader.append(tag_data)
        await self._fetch_parent(broader, parent)

    async def _get_parent(self, parent_id: str):
        data = {"uuid": parent_id}
        return (
            await self._request(
                "concept/get",
                data,
                params=dict(
                    operation="id",
                    conceptFields="uuid,title,type,shortDescription,aliases,source,weight,broader",
                ),
            )
        )["result"][0]

    async def create(self, data: dict) -> dict:
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

        r_data = await self._request("concept/create", concept)

        if r_data["error"]:
            raise SuperdeskApiError.proxyError(
                "iMatrics concept creation failed: {msg}".format(msg=r_data.get("response", ""))
            )

        return {}

    async def delete(self, data: dict) -> dict:
        try:
            uuid = data["uuid"].strip()
            if not uuid:
                raise KeyError
        except KeyError:
            raise SuperdeskApiError.badRequestError(_("[{name}] no tag UUID specified").format(name=self.name))

        await self._request("concept/delete", method="DELETE", params={"uuid": data["uuid"]})
        return {}

    async def data_operation(self, verb: str, operation: str, name: Optional[str], data: dict) -> dict:
        if not self.base_url or not self.user or not self.key:
            logger.warning("IMatrics is not configured propertly, can't analyze article")
            return {}
        if operation == "search":
            self.check_verb("POST", verb, operation)
            return await self.search(data)
        elif operation == "create":
            self.check_verb("POST", verb, operation)
            return await self.create(data)
        elif operation == "delete":
            self.check_verb("POST", verb, operation)
            return await self.delete(data)
        elif operation == "feedback":
            self.check_verb("POST", verb, operation)
            return await self.feedback(data)
        else:
            raise SuperdeskApiError.badRequestError(
                "[{name}] Unexpected operation: {operation}".format(name=name, operation=operation)
            )

    async def publish(self, data):
        return await self._request("article/store", data)

    async def feedback(self, data):
        payload = self._transform_to_imatrics(data["item"], publish=True)
        payload["concepts"] = self._format_concepts(data["tags"])
        await self.publish(payload)
        return {}

    async def _request(
        self, service: str, data: dict | None = None, method: str = "POST", params: dict | None = None
    ) -> dict:
        url = urljoin(self.base_url, service)

        http_client = await self.http_session()
        async with http_client.request(method, url, json=data, auth=self.auth_header, params=params) as r:
            if r.status != 200:
                raise SuperdeskApiError.proxyError(
                    "Unexpected return code ({status_code}) from {name}: {msg}".format(
                        name=self.name,
                        status_code=r.status,
                        msg=r.text,
                    )
                )
            return await r.json()

    async def _request_images(
        self, service: str, data: list[dict] | None = None, method: str = "POST", params: dict | None = None
    ) -> list[dict]:
        url = urljoin(self.image_base_url, service)

        http_client = await self.http_session()
        async with http_client.request(
            method, url, json=data, headers={"x-api-key": self.image_key}, params=params
        ) as r:
            if r.status != 200:
                raise SuperdeskApiError.proxyError(
                    "Unexpected return code ({status_code}) from {name}: {msg}".format(
                        name=self.name,
                        status_code=r.status,
                        msg=r.text,
                    )
                )
            return await r.json()

    def _format_concepts(self, tags):
        concepts = []
        if tags.get("subject"):
            concepts.extend(
                [
                    {
                        "title": subj["name"],
                        "type": "topic" if subj.get("scheme") == "imatrics_topic" else "category",
                        "uuid": subj["altids"]["imatrics"],
                    }
                    for subj in tags["subject"]
                    if subj.get("altids") and subj["altids"].get("imatrics")
                ]
            )
        for _type in ("organisation", "person", "place", "event", "object"):
            if not tags.get(_type):
                continue
            concepts.extend(
                [
                    {
                        "type": _type,
                        "title": concept["name"],
                        "uuid": concept["altids"]["imatrics"],
                    }
                    for concept in tags[_type]
                    if concept.get("altids") and concept["altids"].get("imatrics")
                ]
            )
        return concepts


def get_item_body(item):
    body = []
    for field in ("body_html", "abstract"):
        try:
            body.extend([p.strip() for p in get_text(item[field], "html", True).split("\n") if p.strip()])
        except KeyError:
            pass
    return body


def init_app(app):
    IMatrics(app)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from datetime import datetime, timezone
from typing import Any

from eve.utils import ParsedRequest

from superdesk import get_resource_service
from superdesk.core import json
from superdesk.entity_preview.actor import actor_context
from superdesk.entity_preview.models import EntityPreview, EntityRef, ParsedClientUrl, PreviewLevel
from superdesk.entity_preview.registry import register_handler
from superdesk.entity_preview.urls import get_item_url
from superdesk.users.services import get_display_name
from superdesk.utc import get_date, utcnow


logger = logging.getLogger(__name__)

CONTENT_ENTITY_TYPE = "content"

#: Repos the visibility check searches, mirroring what the client monitoring and search views list.
SEARCH_REPOS = "archive,published,archived"

#: The only item fields a preview is ever built from. Everything else, in particular the item body,
#: notes and scheduling metadata, must never reach an external renderer.
ALLOWED_SOURCE_FIELDS = (
    "_id",
    "item_id",
    "type",
    "state",
    "headline",
    "slugline",
    "byline",
    "authors",
    "original_creator",
    "versioncreated",
    "task",
)

TYPE_LABELS = {
    "text": "Text story",
    "picture": "Picture",
    "video": "Video",
    "audio": "Audio",
    "graphic": "Graphic",
    "composite": "Package",
    "preformatted": "Preformatted",
}

STATE_LABELS = {
    "in_progress": "In progress",
    "being_corrected": "Being corrected",
}

GENERIC_TITLE = "Superdesk content item"

#: States that only ever get a generic preview.
GENERIC_STATES = ("spiked", "killed", "recalled")

#: Flags that only ever get a generic preview.
GENERIC_FLAGS = ("marked_for_legal", "marked_for_not_publication")


def _pick_allowed(entity: dict) -> dict:
    """Copy of the item holding only ``ALLOWED_SOURCE_FIELDS``."""

    return {key: entity[key] for key in ALLOWED_SOURCE_FIELDS if key in entity}


def get_archive_id(entity: dict) -> str:
    """Archive id of a content item, whichever repo it was loaded from.

    ``published`` and ``archived`` documents keep the archive id in ``item_id`` and use their own
    ``_id`` (``PublishedItemService.set_defaults``). Reading them through ``find_one_async`` or the
    search cursor skips ``enhance_with_archive_items``, so the two fields are never swapped here.
    """

    return str(entity.get("item_id") or entity.get("_id") or "")


def get_embargo(entity: dict) -> datetime | None:
    """UTC embargo of an item, or None when it has none or an unusable one."""

    schedule_settings = entity.get("schedule_settings") or {}
    value = schedule_settings.get("utc_embargo") or entity.get("embargo")
    if not value:
        return None

    if isinstance(value, str):
        try:
            value = get_date(value)
        except Exception:
            logger.warning("ignoring unparsable embargo %r on item %s", value, entity.get("_id"))
            return None

    if not isinstance(value, datetime):
        return None

    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def requires_generic_preview(entity: dict) -> bool:
    """Whether an item may only be shown as a generic placeholder.

    This is the single place holding the external preview rules. If the Slack app becomes a product
    these want to be configurable per instance, and it is worth reconsidering whether the restricted
    cases should collapse into ``PreviewLevel.NONE`` (no preview at all) instead of a placeholder
    that still confirms the item exists.
    """

    embargo = get_embargo(entity)
    if embargo and embargo > utcnow():
        return True

    flags = entity.get("flags") or {}
    if any(flags.get(flag) for flag in GENERIC_FLAGS):
        return True

    return entity.get("state") in GENERIC_STATES


class ContentHandler:
    """Preview handler for archive and published content items."""

    type = CONTENT_ENTITY_TYPE

    def match(self, parsed: ParsedClientUrl) -> str | None:
        path = parsed.path.rstrip("/") or "/"

        if path.startswith("/authoring/"):
            segment = path[len("/authoring/") :].split("/")[0]
            return parsed.query.get("_id") or segment or None

        if path == "/search" or path == "/workspace" or path.startswith("/workspace/"):
            if path == "/workspace/assignments":
                # Assignments are planning entities, handled by the planning handler.
                return None
            return parsed.query.get("item") or None

        return None

    async def load(self, entity_id: str) -> dict | None:
        item = await get_resource_service("archive").find_one_async(req=None, _id=entity_id)
        if item:
            return item

        published_service = get_resource_service("published")
        cursor = await published_service.get_from_mongo_async(req=None, lookup={"item_id": entity_id})
        versions = await cursor.to_list()
        if not versions:
            return None

        return max(versions, key=lambda version: version.get("_current_version") or 0)

    async def can_view(self, user_id: str, entity: dict) -> bool:
        """Whether the user would find this item in a Superdesk view they can open.

        Runs the federated search as that user rather than reimplementing the rules, so the answer
        follows ``private_content_filter``, the archive base filter and the invisible stage
        exclusion. Fails closed on any error.
        """

        item_id = get_archive_id(entity)
        if not item_id:
            return False

        try:
            user = await get_resource_service("users").find_one_async(req=None, _id=user_id)
        except Exception:
            logger.warning("could not load user %s for a content preview check", user_id, exc_info=True)
            return False

        if not user or not user.get("is_active") or not user.get("is_enabled"):
            return False

        query = {
            "query": {
                "bool": {
                    "should": [
                        {"ids": {"values": [item_id]}},
                        {"term": {"item_id": item_id}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "size": 5,
        }

        req = ParsedRequest()
        req.args = {"source": json.dumps(query), "repo": SEARCH_REPOS}

        try:
            async with actor_context(user):
                cursor = await get_resource_service("search").get_async(req, lookup=None, signals=False)
                async for doc in cursor:
                    if get_archive_id(doc) == item_id:
                        return True
        except Exception:
            logger.warning("content preview visibility check failed for item %s", item_id, exc_info=True)
            return False

        return False

    def policy(self, entity: dict) -> PreviewLevel:
        return PreviewLevel.GENERIC if requires_generic_preview(entity) else PreviewLevel.FULL

    async def to_preview(self, entity: dict, level: PreviewLevel) -> EntityPreview:
        source = _pick_allowed(entity)
        item_id = get_archive_id(source)
        ref = EntityRef(type=self.type, id=item_id)
        url = self.canonical_url(item_id)

        if level != PreviewLevel.FULL:
            return EntityPreview(
                ref=ref,
                level=level,
                title=GENERIC_TITLE,
                type_label=self._type_label(source),
                fields=[],
                status=None,
                updated=None,
                url=url,
            )

        headline = (source.get("headline") or "").strip()
        slugline = (source.get("slugline") or "").strip()
        title = headline or slugline or "Untitled"

        fields: list[tuple[str, str]] = []
        desk_name, stage_name = await self._task_names(source)
        if desk_name:
            fields.append(("Desk", desk_name))
        if stage_name:
            fields.append(("Stage", stage_name))

        author = await self._author(source)
        if author:
            fields.append(("Author", author))

        if headline and slugline and slugline != title:
            fields.append(("Slugline", slugline))

        return EntityPreview(
            ref=ref,
            level=level,
            title=title,
            type_label=self._type_label(source),
            fields=fields,
            status=self._status_label(source.get("state")),
            updated=source.get("versioncreated"),
            url=url,
        )

    def canonical_url(self, entity_id: str) -> str:
        return get_item_url(entity_id)

    @staticmethod
    def _type_label(source: dict) -> str:
        item_type = source.get("type") or "text"
        return TYPE_LABELS.get(item_type, str(item_type).capitalize())

    @staticmethod
    def _status_label(state: Any) -> str | None:
        if not state:
            return None
        return STATE_LABELS.get(state, str(state).replace("_", " ").capitalize())

    @staticmethod
    async def _task_names(source: dict) -> tuple[str | None, str | None]:
        task = source.get("task") or {}
        desk_name = None
        stage_name = None

        if task.get("desk"):
            desk = await get_resource_service("desks").find_one_async(req=None, _id=task["desk"])
            desk_name = (desk or {}).get("name")

        if task.get("stage"):
            stage = await get_resource_service("stages").find_one_async(req=None, _id=task["stage"])
            stage_name = (stage or {}).get("name")

        return desk_name, stage_name

    @staticmethod
    async def _author(source: dict) -> str | None:
        for author in source.get("authors") or []:
            name = (author or {}).get("name")
            if name:
                return str(name)

        byline = source.get("byline")
        if byline:
            return str(byline)

        if source.get("original_creator"):
            user = await get_resource_service("users").find_one_async(req=None, _id=source["original_creator"])
            if user:
                return get_display_name(user)

        return None


content_handler = ContentHandler()

register_handler(content_handler)

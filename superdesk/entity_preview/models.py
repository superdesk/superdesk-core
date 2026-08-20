# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class PreviewLevel(str, Enum):
    """How much of an entity may be shown outside Superdesk."""

    FULL = "full"
    GENERIC = "generic"
    NONE = "none"


@dataclass(frozen=True)
class EntityRef:
    type: str
    id: str


@dataclass
class ParsedClientUrl:
    """A Superdesk client URL split into the parts the handlers match on.

    ``path`` and ``query`` come from the hash fragment, not from the HTTP path, because the
    Superdesk client uses hash routing (``https://host/#/workspace?item=x&action=view``).
    """

    host: str
    path: str
    query: dict[str, str] = field(default_factory=dict)


@dataclass
class EntityPreview:
    """Renderer-agnostic description of an entity, ready to be turned into a rich link preview."""

    ref: EntityRef
    level: PreviewLevel
    title: str
    type_label: str
    fields: list[tuple[str, str]]
    status: str | None
    updated: datetime | None
    url: str


@runtime_checkable
class EntityHandler(Protocol):
    """Everything the unfurl pipeline needs to know about one kind of entity.

    Handlers live next to the app that owns the entity (content here, planning in
    superdesk-planning) and are plugged in through ``register_handler``.
    """

    type: str

    def match(self, parsed: ParsedClientUrl) -> str | None:
        """Return the entity id this URL points at, or None if it points at something else."""
        ...

    async def load(self, entity_id: str) -> Any | None:
        """Load the entity at the service layer, without any access check."""
        ...

    async def can_view(self, user_id: str, entity: Any) -> bool:
        """Whether the given Superdesk user would find this entity in the Superdesk UI."""
        ...

    def policy(self, entity: Any) -> PreviewLevel:
        """How much of the entity may be shown in a channel anyone can read."""
        ...

    async def to_preview(self, entity: Any, level: PreviewLevel) -> EntityPreview:
        ...

    def canonical_url(self, entity_id: str) -> str:
        ...

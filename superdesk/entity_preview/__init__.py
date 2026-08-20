# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Renderer-agnostic previews of Superdesk entities behind a client URL.

Nothing here knows about Slack. A handler per entity type resolves a client URL to an entity,
answers whether a given user may see it, decides how much of it may be shown outside Superdesk,
and builds an ``EntityPreview`` for a renderer to format.
"""

from superdesk.entity_preview.models import (
    EntityHandler,
    EntityPreview,
    EntityRef,
    ParsedClientUrl,
    PreviewLevel,
)
from superdesk.entity_preview.registry import (
    clear_handlers,
    get_handler,
    get_handlers,
    parse_client_url,
    register_handler,
    resolve_url,
)
from superdesk.entity_preview.urls import get_client_url, get_item_url

# Imported for the side effect of registering the content handler.
from superdesk.entity_preview import content  # noqa: F401


__all__ = [
    "EntityHandler",
    "EntityPreview",
    "EntityRef",
    "ParsedClientUrl",
    "PreviewLevel",
    "clear_handlers",
    "get_client_url",
    "get_handler",
    "get_handlers",
    "get_item_url",
    "parse_client_url",
    "register_handler",
    "resolve_url",
]

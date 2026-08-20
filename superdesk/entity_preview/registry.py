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

from urllib.parse import parse_qsl, unquote, urlsplit

from superdesk.entity_preview.models import EntityHandler, EntityRef, ParsedClientUrl
from superdesk.entity_preview.urls import get_client_url


logger = logging.getLogger(__name__)

_handlers: dict[str, EntityHandler] = {}

ALLOWED_SCHEMES = ("http", "https")


def register_handler(handler: EntityHandler) -> None:
    """Register a handler, replacing any previous handler for the same entity type."""

    _handlers[handler.type] = handler


def get_handler(entity_type: str) -> EntityHandler | None:
    return _handlers.get(entity_type)


def get_handlers() -> list[EntityHandler]:
    return list(_handlers.values())


def clear_handlers() -> None:
    _handlers.clear()


def _host_key(host: str | None, port: int | None) -> str | None:
    """Comparable host, keeping an explicit port so ``host:8080`` never matches ``host``."""

    if not host:
        return None
    return "{}:{}".format(host.lower(), port) if port else host.lower()


def parse_client_url(url: str) -> ParsedClientUrl | None:
    """Split a Superdesk client URL into the fragment path and query the handlers match on.

    Returns None unless the URL is an http(s) URL on exactly the ``CLIENT_URL`` host (no
    subdomains), under the ``CLIENT_URL`` path, and carrying a hash fragment starting with ``/``.
    """

    if not url or not isinstance(url, str):
        return None

    try:
        parsed = urlsplit(url.strip())
        url_host = _host_key(parsed.hostname, parsed.port)
    except ValueError:
        return None

    if parsed.scheme not in ALLOWED_SCHEMES or not url_host:
        return None

    try:
        client = urlsplit(get_client_url())
        client_host = _host_key(client.hostname, client.port)
    except ValueError:
        return None

    if not client_host or url_host != client_host:
        return None

    client_path = client.path.rstrip("/")
    if client_path and not parsed.path.startswith(client_path):
        return None

    fragment = parsed.fragment
    if not fragment.startswith("/"):
        return None

    fragment_path, _, fragment_query = fragment.partition("?")
    query: dict[str, str] = {}
    for key, value in parse_qsl(fragment_query, keep_blank_values=True):
        query.setdefault(key, value)

    return ParsedClientUrl(host=url_host, path=unquote(fragment_path), query=query)


def resolve_url(url: str) -> EntityRef | None:
    """Resolve a Superdesk client URL to the entity it points at."""

    parsed = parse_client_url(url)
    if parsed is None:
        return None

    for handler in get_handlers():
        try:
            entity_id = handler.match(parsed)
        except Exception:
            logger.warning("entity preview handler %s failed to match a url", handler.type, exc_info=True)
            continue
        if entity_id:
            return EntityRef(type=handler.type, id=entity_id)

    return None

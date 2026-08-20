# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import logging
import secrets
from typing import Any

from superdesk.core import get_app_config, get_current_app

from .client import get_slack_client


logger = logging.getLogger(__name__)

#: A link token is only meant to survive the round trip from the Slack prompt to the browser
LINK_TOKEN_TTL = 600

REDIS_KEY_PREFIX = "slack:link:"

PENDING_KEY_PREFIX = "slack:pending:"


def _redis_key(token: str) -> str:
    return f"{REDIS_KEY_PREFIX}{token}"


def _pending_key(team_id: str, slack_user_id: str) -> str:
    return f"{PENDING_KEY_PREFIX}{team_id}:{slack_user_id}"


def _decode(raw: Any) -> dict | None:
    if not raw:
        return None

    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("slack link token payload is not valid JSON")
        return None

    return data if isinstance(data, dict) else None


def create_link_token(team_id: str, slack_user_id: str, channel: str | None = None) -> str:
    """Store the Slack side of a pending link and return the token identifying it.

    The token travels in the URL sent to the Slack user, the Superdesk side of the link comes from
    the session of the browser that opens it.
    """

    token = secrets.token_urlsafe(32)
    payload = json.dumps({"team_id": team_id, "slack_user_id": slack_user_id, "channel": channel})
    get_current_app().redis.set(_redis_key(token), payload, ex=LINK_TOKEN_TTL)
    return token


def peek_link_token(token: str) -> dict | None:
    """Read a link token without consuming it, for pages that only display what would be linked."""

    return _decode(get_current_app().redis.get(_redis_key(token)))


def consume_link_token(token: str) -> dict | None:
    """Read a link token and delete it, so a token can only create one link."""

    return _decode(get_current_app().redis.getdel(_redis_key(token)))


def store_pending_unfurl(team_id: str, slack_user_id: str, payload: dict) -> None:
    """Keep the ``link_shared`` event of an unlinked Slack user until they connect their account.

    ``payload`` is the keyword arguments of the unfurl task, so connecting can replay the event
    instead of asking the user to paste the link again. It lives as long as the link token, one
    entry per Slack user: only the last link they shared is worth replaying.
    """

    get_current_app().redis.set(_pending_key(team_id, slack_user_id), json.dumps(payload), ex=LINK_TOKEN_TTL)


def pop_pending_unfurl(team_id: str, slack_user_id: str) -> dict | None:
    """Read the pending unfurl of a Slack user and delete it, so it is replayed at most once."""

    return _decode(get_current_app().redis.getdel(_pending_key(team_id, slack_user_id)))


def get_link_url(token: str) -> str:
    server_url = str(get_app_config("SERVER_URL") or "")
    return f"{server_url.rstrip('/')}/slack/link?t={token}"


async def notify_slack_user(channel: str | None, slack_user_id: str, text: str) -> None:
    """Send an ephemeral message to a Slack user, best effort.

    Nothing here is worth failing a request the user already completed, so every error is logged
    and swallowed.
    """

    if not channel:
        return

    client = get_slack_client()
    if client is None:
        return

    try:
        await client.chat_postEphemeral(channel=channel, user=slack_user_id, text=text)
    except Exception:
        logger.warning("could not notify slack user=%s channel=%s", slack_user_id, channel, exc_info=True)

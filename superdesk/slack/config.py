# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core import get_app_config


def _get_str_config(key: str) -> str:
    value = get_app_config(key)
    return value.strip() if isinstance(value, str) else ""


def get_signing_secret() -> str:
    """Slack app signing secret, used to verify the requests Slack sends us."""

    return _get_str_config("SLACK_SIGNING_SECRET")


def get_bot_token() -> str:
    """Bot user OAuth token, used to call the Slack API."""

    return _get_str_config("SLACK_BOT_TOKEN")


def is_configured() -> bool:
    """Whether the events endpoint can serve requests.

    Only the signing secret matters here: without it no request can be trusted, so the
    endpoint behaves as if it did not exist. The bot token is only needed to call Slack back.
    """

    return bool(get_signing_secret())


def get_team_id() -> str | None:
    """Workspace the app is installed in, or ``None`` when events from any workspace are accepted."""

    return _get_str_config("SLACK_TEAM_ID") or None


def get_app_id() -> str | None:
    """Slack app the events must come from, or ``None`` when events from any app are accepted."""

    return _get_str_config("SLACK_APP_ID") or None

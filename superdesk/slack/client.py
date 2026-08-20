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

from slack_sdk.web.async_client import AsyncWebClient

from .config import get_bot_token


logger = logging.getLogger(__name__)


def get_slack_client() -> AsyncWebClient | None:
    """Client for the Slack Web API, or ``None`` when no bot token is configured."""

    token = get_bot_token()
    if not token:
        return None

    return AsyncWebClient(token=token)

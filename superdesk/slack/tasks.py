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

from superdesk.celery_app import celery


logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=30)
async def unfurl_links(
    team_id: str,
    channel: str | None,
    message_ts: str | None,
    thread_ts: str | None,
    unfurl_id: str | None,
    source: str | None,
    slack_user_id: str | None,
    links: list[str],
    event_id: str | None,
) -> None:
    """Handle a Slack ``link_shared`` event outside the request cycle.

    Resolving the links and posting the unfurls back to Slack is implemented in a later phase.
    """

    logger.info(
        "slack unfurl_links event_id=%s team=%s user=%s links=%d",
        event_id,
        team_id,
        slack_user_id,
        len(links),
    )

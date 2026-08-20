# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Turning a Slack ``link_shared`` event into rich previews, outside the request cycle.

A preview is built with the permissions of the Superdesk user the sharing Slack user is linked to,
and every step fails closed: anything unexpected drops the URL rather than showing more of it.
"""

import logging

from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from superdesk.celery_app import celery
from superdesk.entity_preview import EntityPreview, EntityRef, PreviewLevel, get_handler, resolve_url

from .client import get_slack_client
from .linking import create_link_token, get_link_url, store_pending_unfurl
from .render import render_unfurls
from .resources import SlackUserLinksService


logger = logging.getLogger(__name__)

CONNECT_MESSAGE = "Connect your Slack account to Superdesk to preview its links here. Only you can see this message."

COMPOSER_SOURCE = "composer"


async def _chat_unfurl(
    client: AsyncWebClient,
    *,
    channel: str | None,
    message_ts: str | None,
    unfurl_id: str | None,
    source: str | None,
    **kwargs: Any,
) -> bool:
    """Call ``chat.unfurl`` with whichever pair of identifiers the event carries.

    A link typed in the message composer is not a message yet and is only addressable by its
    ``unfurl_id``. Returns whether Slack accepted the call.
    """

    if source == COMPOSER_SOURCE and unfurl_id:
        target: dict[str, Any] = {"unfurl_id": unfurl_id, "source": source}
    elif channel and message_ts:
        target = {"channel": channel, "ts": message_ts}
    else:
        logger.warning("slack unfurl skipped, the event identifies neither a message nor a composer preview")
        return False

    try:
        await client.chat_unfurl(**target, **kwargs)
    except SlackApiError as error:
        response = getattr(error, "response", None)
        logger.warning("slack chat.unfurl failed error=%s", response.get("error") if response is not None else None)
        return False
    except Exception:
        logger.warning("slack chat.unfurl failed", exc_info=True)
        return False

    return True


async def _build_preview(ref: EntityRef, user_id: str) -> tuple[EntityPreview | None, str]:
    """Preview of one entity for one Superdesk user, with the outcome to log for it."""

    handler = get_handler(ref.type)
    if handler is None:
        return None, "unsupported"

    entity = await handler.load(ref.id)
    if entity is None:
        return None, "not_found"

    if not await handler.can_view(user_id, entity):
        return None, "forbidden"

    level = handler.policy(entity)
    if level == PreviewLevel.NONE:
        return None, level.value

    return await handler.to_preview(entity, level), level.value


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
    """Post the previews of the Superdesk links of one ``link_shared`` event back to Slack.

    An unlinked Slack user gets the connect prompt instead, and the event is kept so that
    connecting replays it.
    """

    client = get_slack_client()
    if client is None:
        logger.info("slack unfurl skipped, no bot token")
        return

    refs = {url: ref for url, ref in ((url, resolve_url(url)) for url in links) if ref is not None}
    if not refs:
        logger.debug("slack unfurl event_id=%s carries no supported link", event_id)
        return

    if not slack_user_id:
        logger.warning("slack unfurl skipped, event_id=%s names no slack user", event_id)
        return

    link = await SlackUserLinksService().find_by_slack_user(team_id, slack_user_id)

    if link is None:
        store_pending_unfurl(
            team_id,
            slack_user_id,
            {
                "team_id": team_id,
                "channel": channel,
                "message_ts": message_ts,
                "thread_ts": thread_ts,
                "unfurl_id": unfurl_id,
                "source": source,
                "slack_user_id": slack_user_id,
                "links": links,
                "event_id": event_id,
            },
        )
        token = create_link_token(team_id, slack_user_id, channel)

        # An empty ``unfurls`` map is what turns this call into the auth prompt Slack shows to the
        # sharing user only. Nothing about the entity may be sent here, the user is not linked yet.
        sent = await _chat_unfurl(
            client,
            channel=channel,
            message_ts=message_ts,
            unfurl_id=unfurl_id,
            source=source,
            unfurls={},
            user_auth_required=True,
            user_auth_url=get_link_url(token),
            user_auth_message=CONNECT_MESSAGE,
        )
        if sent:
            logger.info("slack unfurl prompt sent team=%s user=%s", team_id, slack_user_id)
        return

    user_id = str(link.user)
    previews: dict[str, EntityPreview] = {}

    for url, ref in refs.items():
        try:
            preview, outcome = await _build_preview(ref, user_id)
        except Exception:
            logger.warning("slack unfurl failed to build a preview of %s:%s", ref.type, ref.id, exc_info=True)
            preview, outcome = None, "error"

        if preview is not None:
            previews[url] = preview

        logger.info(
            "slack unfurl event_id=%s team=%s user=%s entity=%s:%s outcome=%s",
            event_id,
            team_id,
            slack_user_id,
            ref.type,
            ref.id,
            outcome,
        )

    unfurls = render_unfurls(previews)
    if not unfurls:
        logger.debug("slack unfurl event_id=%s has nothing to show", event_id)
        return

    sent = await _chat_unfurl(
        client,
        channel=channel,
        message_ts=message_ts,
        unfurl_id=unfurl_id,
        source=source,
        unfurls=unfurls,
    )
    if sent:
        logger.info("slack unfurl posted event_id=%s urls=%d", event_id, len(unfurls))

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
from typing import Any

from superdesk.core.types import Request, Response
from superdesk.core.web import EndpointGroup

from .config import get_app_id, get_team_id, is_configured
from .signature import verify_slack_request
from .tasks import unfurl_links


logger = logging.getLogger(__name__)

slack_endpoints = EndpointGroup("slack", __name__)


async def enqueue_unfurl(**kwargs: Any) -> None:
    await unfurl_links.apply_async(kwargs=kwargs)


@slack_endpoints.endpoint("slack/events", "slack_events", methods=["POST"], auth=False, cors=False)
async def slack_events(request: Request) -> Response:
    """Single entry point for the Slack Events API.

    Slack retries an event when it does not get a 2xx answer within three seconds, so this handler
    stays free of database and Slack API calls and hands the work to a Celery task.
    """

    if not is_configured():
        return Response("", 404, ())

    body = await request.get_data()
    signature_headers = {
        "X-Slack-Signature": request.get_header("X-Slack-Signature") or "",
        "X-Slack-Request-Timestamp": request.get_header("X-Slack-Request-Timestamp") or "",
    }

    if not verify_slack_request(signature_headers, body):
        logger.warning("slack request rejected, signature verification failed")
        return Response("", 401, ())

    try:
        payload = json.loads(body)
    except ValueError:
        payload = None

    if not isinstance(payload, dict):
        # Answer 200 anyway: a body Slack cannot have sent will not become valid on a retry
        logger.warning("slack request body is not a JSON object")
        return Response("", 200, ())

    payload_type = payload.get("type")

    if payload_type == "url_verification":
        return Response({"challenge": payload.get("challenge")}, 200, ())

    if payload_type != "event_callback":
        return Response("", 200, ())

    team_id = payload.get("team_id") or ""
    expected_team_id = get_team_id()
    if expected_team_id and team_id != expected_team_id:
        logger.warning("slack event ignored, it comes from another workspace")
        return Response("", 200, ())

    expected_app_id = get_app_id()
    if expected_app_id and payload.get("api_app_id") != expected_app_id:
        logger.warning("slack event ignored, it comes from another Slack app")
        return Response("", 200, ())

    event = payload.get("event") or {}
    if event.get("type") != "link_shared":
        return Response("", 200, ())

    links = [link["url"] for link in event.get("links") or [] if link.get("url")]
    retry_num = request.get_header("X-Slack-Retry-Num")

    logger.info(
        "slack link_shared event_id=%s team=%s channel=%s user=%s links=%d%s",
        payload.get("event_id"),
        team_id,
        event.get("channel"),
        event.get("user"),
        len(links),
        f" retry={retry_num}" if retry_num else "",
    )

    await enqueue_unfurl(
        team_id=team_id,
        channel=event.get("channel"),
        message_ts=event.get("message_ts"),
        thread_ts=event.get("thread_ts"),
        unfurl_id=event.get("unfurl_id"),
        source=event.get("source"),
        slack_user_id=event.get("user"),
        links=links,
        event_id=payload.get("event_id"),
    )

    return Response("", 200, [("X-Slack-No-Retry", "1")])

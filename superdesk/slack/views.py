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

from superdesk.core import get_app_config, get_current_async_app
from superdesk.core.types import Request, Response
from superdesk.core.web import EndpointGroup
from superdesk.errors import SuperdeskApiError
from superdesk.flask import render_template

from .config import get_app_id, get_team_id, is_configured
from .linking import consume_link_token, notify_slack_user, peek_link_token
from .resources import LINK_METHOD_BROWSER, SlackLinkConflict, SlackUserLinksService
from .signature import verify_slack_request
from .tasks import unfurl_links


logger = logging.getLogger(__name__)

slack_endpoints = EndpointGroup("slack", __name__)

SESSION_NONCE_KEY = "slack_link_nonce"

TOKEN_GONE_MESSAGE = (
    "This link has expired or was already used. Paste the Superdesk link in Slack again to get a new one."
)
NONCE_MISMATCH_MESSAGE = "This page has expired. Paste the Superdesk link in Slack again to get a new one."


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


def _client_url() -> str:
    return str(get_app_config("CLIENT_URL") or "")


def _user_name(user: dict) -> str:
    return user.get("display_name") or user.get("username") or ""


async def _get_session_user(request: Request) -> dict | None:
    """Authenticate the request from the Superdesk session cookie.

    These endpoints are opened by a browser navigation rather than by the client, so there is no
    ``Authorization`` header, only the ``session_token`` cookie Superdesk sets on every
    authenticated API request. Returns ``None`` when there is no usable session.
    """

    try:
        await get_current_async_app().auth.authenticate(request)
    except SuperdeskApiError:
        return None

    return request.user


async def _html(template: str, status_code: int = 200, **context: Any) -> Response:
    html = await render_template(template, **context)
    return Response(html, status_code, [("Content-Type", "text/html; charset=utf-8")])


async def _error_page(
    message: str,
    status_code: int = 400,
    title: str = "Connect Slack to Superdesk",
    link_url: str | None = None,
    link_label: str | None = None,
) -> Response:
    return await _html(
        "slack_link_error.html",
        status_code,
        title=title,
        message=message,
        link_url=link_url,
        link_label=link_label,
    )


def _issue_nonce(request: Request) -> str:
    nonce = secrets.token_urlsafe(16)
    request.storage.session.set(SESSION_NONCE_KEY, nonce)
    return nonce


def _consume_nonce(request: Request, value: Any) -> bool:
    expected = request.storage.session.get(SESSION_NONCE_KEY)
    request.storage.session.pop(SESSION_NONCE_KEY, None)

    if not expected or not isinstance(value, str) or not value:
        return False

    return secrets.compare_digest(value, expected)


def _disconnect_url(request: Request) -> str:
    return f"{request.path.rstrip('/')}/disconnect"


@slack_endpoints.endpoint("slack/link", "slack_link", methods=["GET"], auth=False, cors=False)
async def slack_link(request: Request) -> Any:
    """Confirmation page for linking the Slack user named by the token to the logged in user."""

    if not is_configured():
        return Response("", 404, ())

    token = request.get_url_arg("t")
    if not token:
        return await _error_page("This link is not valid.")

    user = await _get_session_user(request)
    if user is None:
        # The user is sent to the client to log in, then clicks the button in Slack again
        return request.redirect(_client_url())

    data = peek_link_token(token)
    if data is None:
        return await _error_page(TOKEN_GONE_MESSAGE)

    existing = await SlackUserLinksService().find_by_user(user["_id"])

    return await _html(
        "slack_link_confirm.html",
        user_name=_user_name(user),
        team_id=data.get("team_id"),
        slack_user_id=data.get("slack_user_id"),
        token=token,
        nonce=_issue_nonce(request),
        action=request.path,
        disconnect_url=_disconnect_url(request),
        linked_slack_user_id=existing.slack_user_id if existing is not None else None,
    )


# The mutations below are POST only. A GET that mutates would be triggerable from any other site,
# because SameSite=Lax still sends the session cookie on a top level navigation. The nonce carried
# in the signed session cookie makes a cross-site form post fail as well.
@slack_endpoints.endpoint("slack/link", "slack_link_submit", methods=["POST"], auth=False, cors=False)
async def slack_link_submit(request: Request) -> Any:
    if not is_configured():
        return Response("", 404, ())

    user = await _get_session_user(request)
    if user is None:
        return request.redirect(_client_url())

    form = await request.get_form()
    token = form.get("t")
    if not token or not _consume_nonce(request, form.get("nonce")):
        return await _error_page(NONCE_MISMATCH_MESSAGE)

    data = consume_link_token(token)
    if data is None:
        return await _error_page(TOKEN_GONE_MESSAGE)

    team_id = data.get("team_id") or ""
    slack_user_id = data.get("slack_user_id") or ""
    disconnect_url = _disconnect_url(request)

    try:
        await SlackUserLinksService().link(team_id, slack_user_id, user["_id"], LINK_METHOD_BROWSER)
    except SlackLinkConflict as conflict:
        if conflict.reason == "slack_user_linked":
            return await _error_page(
                f"Slack user {slack_user_id} is already connected to another Superdesk account. "
                "That account has to disconnect it first, or an administrator can run "
                "the slack:unlink_user command.",
                409,
            )

        return await _error_page(
            f"Superdesk account {_user_name(user)} is already connected to a different Slack user.",
            409,
            link_url=disconnect_url,
            link_label="Disconnect it first",
        )

    logger.info(
        "slack link created user=%s slack_user=%s team=%s",
        user["_id"],
        slack_user_id,
        team_id,
    )

    await notify_slack_user(
        data.get("channel"),
        slack_user_id,
        f"Your Slack account is now connected to Superdesk user {user.get('username')}. "
        "Paste the link again to see its preview.",
    )

    return await _html(
        "slack_link_done.html",
        user_name=_user_name(user),
        slack_user_id=slack_user_id,
        disconnect_url=disconnect_url,
        nonce=_issue_nonce(request),
    )


@slack_endpoints.endpoint("slack/link/disconnect", "slack_link_disconnect", methods=["GET"], auth=False, cors=False)
async def slack_link_disconnect(request: Request) -> Any:
    if not is_configured():
        return Response("", 404, ())

    user = await _get_session_user(request)
    if user is None:
        return request.redirect(_client_url())

    name = _user_name(user)
    link = await SlackUserLinksService().find_by_user(user["_id"])
    if link is None:
        return await _html(
            "slack_link_disconnect.html",
            title="Slack is not connected",
            message=f"No Slack account is linked to {name}.",
        )

    return await _html(
        "slack_link_disconnect.html",
        title="Disconnect Slack",
        message=f"Disconnect Slack user {link.slack_user_id} from {name}?",
        action=request.path,
        nonce=_issue_nonce(request),
    )


# POST for the same reason as ``slack_link_submit``: this removes a row using cookie authentication.
@slack_endpoints.endpoint(
    "slack/link/disconnect", "slack_link_disconnect_submit", methods=["POST"], auth=False, cors=False
)
async def slack_link_disconnect_submit(request: Request) -> Any:
    if not is_configured():
        return Response("", 404, ())

    user = await _get_session_user(request)
    if user is None:
        return request.redirect(_client_url())

    form = await request.get_form()
    if not _consume_nonce(request, form.get("nonce")):
        return await _error_page(NONCE_MISMATCH_MESSAGE, title="Disconnect Slack")

    name = _user_name(user)
    if not await SlackUserLinksService().unlink_user(user["_id"]):
        return await _html(
            "slack_link_disconnect.html",
            title="Slack is not connected",
            message=f"No Slack account is linked to {name}.",
        )

    logger.info("slack link removed user=%s", user["_id"])

    return await _html(
        "slack_link_disconnect.html",
        title="Disconnected",
        message=f"{name} is no longer linked to a Slack account.",
    )

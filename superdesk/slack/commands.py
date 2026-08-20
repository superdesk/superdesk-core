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

import click

from superdesk.commands import cli
from superdesk.types import UsersResourceModel

from .config import get_team_id
from .resources import LINK_METHOD_CLI, SlackLinkConflict, SlackUserLinksService


logger = logging.getLogger(__name__)

CONFLICT_MESSAGES = {
    "slack_user_linked": "that Slack user is already linked to another Superdesk user",
    "user_linked": "that Superdesk user is already linked to another Slack user",
}


async def _get_user(username: str) -> UsersResourceModel:
    user = await UsersResourceModel.get_service().find_one(username=username)
    if user is None:
        raise click.ClickException(f"No Superdesk user with username {username}")

    return user


def _resolve_team(team_id: str | None) -> str:
    team = team_id or get_team_id()
    if not team:
        raise click.ClickException("No Slack workspace given, pass --team or set SLACK_TEAM_ID")

    return team


async def link_user(username: str, slack_user_id: str, team_id: str | None = None) -> str:
    team = _resolve_team(team_id)
    user = await _get_user(username)

    try:
        await SlackUserLinksService().link(team, slack_user_id, user.id, LINK_METHOD_CLI)
    except SlackLinkConflict as conflict:
        raise click.ClickException(
            f"Could not link {username} to {slack_user_id}: "
            f"{CONFLICT_MESSAGES.get(conflict.reason, conflict.reason)}"
        )

    return f"Linked Superdesk user {username} to Slack user {slack_user_id} in workspace {team}"


async def unlink_user(username: str) -> str:
    user = await _get_user(username)

    if not await SlackUserLinksService().unlink_user(user.id):
        raise click.ClickException(f"No Slack user is linked to {username}")

    return f"Unlinked Superdesk user {username}"


async def list_links() -> list[str]:
    links = await SlackUserLinksService().list_links()
    if not links:
        return ["No Slack users are linked"]

    users_service = UsersResourceModel.get_service()
    lines = [f"{'TEAM':<12}{'SLACK USER':<16}{'USERNAME':<24}{'METHOD':<10}LINKED AT"]

    for link in links:
        user = await users_service.find_by_id(link.user)
        username = user.username if user is not None else str(link.user)
        lines.append(
            f"{link.team_id:<12}{link.slack_user_id:<16}{username:<24}" f"{link.method:<10}{link.linked_at.isoformat()}"
        )

    return lines


@cli.command("slack:link_user")
@click.option("--user", "username", required=True, help="Superdesk username")
@click.option("--slack-user", "slack_user_id", required=True, help="Slack user id, for example U012ABCDEF")
@click.option("--team", "team_id", required=False, help="Slack workspace id, defaults to SLACK_TEAM_ID")
async def cli_slack_link_user(username: str, slack_user_id: str, team_id: str | None = None) -> None:
    """Link a Slack user to a Superdesk user.

    Example:
    ::

        $ python manage.py slack:link_user --user jdoe --slack-user U012ABCDEF
        $ python manage.py slack:link_user --user jdoe --slack-user U012ABCDEF --team T012ABCDEF

    """

    click.echo(await link_user(username, slack_user_id, team_id))


@cli.command("slack:unlink_user")
@click.option("--user", "username", required=True, help="Superdesk username")
async def cli_slack_unlink_user(username: str) -> None:
    """Remove the Slack link of a Superdesk user.

    Example:
    ::

        $ python manage.py slack:unlink_user --user jdoe

    """

    click.echo(await unlink_user(username))


@cli.command("slack:list_links")
async def cli_slack_list_links() -> None:
    """List the links between Slack users and Superdesk users.

    Example:
    ::

        $ python manage.py slack:list_links

    """

    for line in await list_links():
        click.echo(line)

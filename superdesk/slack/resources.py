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
from datetime import datetime

from bson import ObjectId

from superdesk.core.resources import (
    AsyncResourceService,
    MongoIndexOptions,
    MongoResourceConfig,
    ResourceConfig,
    ResourceModelWithObjectId,
    fields,
)
from superdesk.utc import utcnow


logger = logging.getLogger(__name__)

RESOURCE_NAME = "slack_user_links"

LINK_METHOD_BROWSER = "browser"
LINK_METHOD_CLI = "cli"


class SlackLinkConflict(Exception):
    """Raised when a link cannot be created because one of the two sides is already linked.

    ``reason`` is ``slack_user_linked`` when the Slack user points at another Superdesk user, and
    ``user_linked`` when the Superdesk user points at another Slack user.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SlackUserLinkResourceModel(ResourceModelWithObjectId):
    team_id: fields.Keyword
    slack_user_id: fields.Keyword
    user: fields.ObjectId
    linked_at: datetime
    method: str


class SlackUserLinksService(AsyncResourceService[SlackUserLinkResourceModel]):
    """Links between Slack users and Superdesk users.

    The collection is written by the server only, there are no REST endpoints for it. A Superdesk
    user and a Slack user can each take part in at most one link.
    """

    async def find_by_slack_user(self, team_id: str, slack_user_id: str) -> SlackUserLinkResourceModel | None:
        return await self.find_one(team_id=team_id, slack_user_id=slack_user_id)

    async def find_by_user(self, user_id: ObjectId | str) -> SlackUserLinkResourceModel | None:
        return await self.find_one(user=ObjectId(user_id))

    async def link(
        self,
        team_id: str,
        slack_user_id: str,
        user_id: ObjectId | str,
        method: str,
    ) -> SlackUserLinkResourceModel:
        """Link a Slack user to a Superdesk user.

        Linking a pair that is already linked returns the existing link instead of creating a
        second one.

        :raises SlackLinkConflict: If either side is already linked to somebody else.
        """

        user = ObjectId(user_id)

        existing_for_slack_user = await self.find_by_slack_user(team_id, slack_user_id)
        if existing_for_slack_user is not None:
            if existing_for_slack_user.user == user:
                return existing_for_slack_user
            raise SlackLinkConflict("slack_user_linked")

        existing_for_user = await self.find_by_user(user)
        if existing_for_user is not None:
            raise SlackLinkConflict("user_linked")

        docs = await self.create(
            [
                SlackUserLinkResourceModel(  # type: ignore[call-arg]
                    team_id=team_id,
                    slack_user_id=slack_user_id,
                    user=user,
                    linked_at=utcnow(),
                    method=method,
                )
            ]
        )
        return docs[0]

    async def unlink_user(self, user_id: ObjectId | str) -> bool:
        """Remove the link of a Superdesk user, returns whether there was one."""

        link = await self.find_by_user(user_id)
        if link is None:
            return False

        await self.delete(link)
        return True

    async def unlink_slack_user(self, team_id: str, slack_user_id: str) -> bool:
        """Remove the link of a Slack user, returns whether there was one."""

        link = await self.find_by_slack_user(team_id, slack_user_id)
        if link is None:
            return False

        await self.delete(link)
        return True

    async def list_links(self) -> list[SlackUserLinkResourceModel]:
        return await self.get_all_list()


slack_user_links_config = ResourceConfig(
    name=RESOURCE_NAME,
    data_class=SlackUserLinkResourceModel,
    service=SlackUserLinksService,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="team_id_slack_user_id",
                keys=[("team_id", 1), ("slack_user_id", 1)],
                unique=True,
                sparse=False,
            ),
            MongoIndexOptions(
                name="team_id_user",
                keys=[("team_id", 1), ("user", 1)],
                unique=True,
                sparse=False,
            ),
        ]
    ),
)

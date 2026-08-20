import click
from bson import ObjectId

from superdesk.slack.commands import link_user, list_links, unlink_user
from superdesk.slack.resources import SlackUserLinksService
from superdesk.tests import TestCase, setup_auth_user
from superdesk.types import UsersResourceModel


TEAM_ID = "T123"


class SlackCommandsTestCase(TestCase):
    app_config = {
        "SLACK_SIGNING_SECRET": "testsecret",
        "SLACK_BOT_TOKEN": "xoxb-test",
        "SLACK_TEAM_ID": TEAM_ID,
    }

    async def asyncSetUp(self):
        await super().asyncSetUp()

        self.headers = [("Content-Type", "application/json")]
        await setup_auth_user(self)

        self.username = self.user["username"]
        user = await UsersResourceModel.get_service().find_one(username=self.username)
        assert user is not None
        self.user_id = user.id
        self.links = SlackUserLinksService()

    async def test_link_user(self):
        output = await link_user(self.username, "U123")

        self.assertIn(self.username, output)
        self.assertIn("U123", output)

        link = await self.links.find_by_user(self.user_id)
        assert link is not None
        self.assertEqual(link.team_id, TEAM_ID)
        self.assertEqual(link.slack_user_id, "U123")
        self.assertEqual(link.method, "cli")

    async def test_link_user_with_explicit_team(self):
        await link_user(self.username, "U123", "T999")

        link = await self.links.find_by_user(self.user_id)
        assert link is not None
        self.assertEqual(link.team_id, "T999")

    async def test_link_user_without_a_team(self):
        self.app.config["SLACK_TEAM_ID"] = ""

        with self.assertRaises(click.ClickException) as context:
            await link_user(self.username, "U123")

        self.assertIn("pass --team or set SLACK_TEAM_ID", context.exception.message)

    async def test_link_unknown_user(self):
        with self.assertRaises(click.ClickException) as context:
            await link_user("nosuchuser", "U123")

        self.assertIn("No Superdesk user with username nosuchuser", context.exception.message)

    async def test_link_user_conflict(self):
        await self.links.link(TEAM_ID, "U123", ObjectId(), "cli")

        with self.assertRaises(click.ClickException) as context:
            await link_user(self.username, "U123")

        self.assertIn("already linked to another Superdesk user", context.exception.message)

    async def test_unlink_user(self):
        await link_user(self.username, "U123")

        output = await unlink_user(self.username)

        self.assertIn(self.username, output)
        self.assertIsNone(await self.links.find_by_user(self.user_id))

    async def test_unlink_user_without_a_link(self):
        with self.assertRaises(click.ClickException) as context:
            await unlink_user(self.username)

        self.assertIn("No Slack user is linked", context.exception.message)

    async def test_list_links_when_empty(self):
        self.assertEqual(await list_links(), ["No Slack users are linked"])

    async def test_list_links(self):
        await link_user(self.username, "U123")

        lines = await list_links()

        self.assertEqual(len(lines), 2)
        self.assertIn("SLACK USER", lines[0])
        self.assertIn(TEAM_ID, lines[1])
        self.assertIn("U123", lines[1])
        self.assertIn(self.username, lines[1])
        self.assertIn("cli", lines[1])

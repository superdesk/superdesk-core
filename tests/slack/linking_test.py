import re
from unittest import mock

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from superdesk import get_resource_service
from superdesk.slack.linking import (
    consume_link_token,
    create_link_token,
    get_link_url,
    peek_link_token,
)
from superdesk.slack.resources import SlackLinkConflict, SlackUserLinksService
from superdesk.tests import TestCase, setup_auth_user
from superdesk.types import UsersResourceModel


LINK_URL = "/api/slack/link"
DISCONNECT_URL = "/api/slack/link/disconnect"
TEAM_ID = "T123"

SLACK_CONFIG = {
    "SLACK_SIGNING_SECRET": "testsecret",
    "SLACK_BOT_TOKEN": "xoxb-test",
    "SLACK_TEAM_ID": TEAM_ID,
}


def nonce_from(html: str) -> str:
    match = re.search(r'name="nonce" value="([^"]+)"', html)
    assert match is not None, html
    return match.group(1)


class SlackLinkingTestCase(TestCase):
    app_config = SLACK_CONFIG

    async def asyncSetUp(self):
        await super().asyncSetUp()

        self.headers = [("Content-Type", "application/json")]
        await setup_auth_user(self)

        # The session cookie is set on any authenticated request, this is what the link pages use
        response = await self.test_client.get("/api/users", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        user = await UsersResourceModel.get_service().find_one(username=self.user["username"])
        assert user is not None
        self.user_id = user.id
        self.links = SlackUserLinksService()

        patcher = mock.patch("superdesk.slack.views.notify_slack_user", new=mock.AsyncMock())
        self.notify_slack_user = patcher.start()
        self.addCleanup(patcher.stop)

    async def get_html(self, url: str) -> tuple[int, str]:
        response = await self.test_client.get(url)
        return response.status_code, await response.get_data(as_text=True)

    async def post_html(self, url: str, form: dict) -> tuple[int, str]:
        response = await self.test_client.post(url, form=form)
        return response.status_code, await response.get_data(as_text=True)

    async def open_confirm_page(self, channel: str | None = "C123", slack_user_id: str = "U123") -> tuple[str, str]:
        token = create_link_token(TEAM_ID, slack_user_id, channel)
        status, html = await self.get_html(f"{LINK_URL}?t={token}")
        self.assertEqual(status, 200, html)
        return token, nonce_from(html)

    async def test_get_link_without_session_redirects_to_client(self):
        token = create_link_token(TEAM_ID, "U123", "C123")
        anonymous = self.app.test_client()

        response = await anonymous.get(f"{LINK_URL}?t={token}")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], self.app.config["CLIENT_URL"])

    async def test_get_link_without_token(self):
        status, html = await self.get_html(LINK_URL)

        self.assertEqual(status, 400)
        self.assertIn("This link is not valid.", html)

    async def test_get_link_with_unknown_token(self):
        status, html = await self.get_html(f"{LINK_URL}?t=nosuchtoken")

        self.assertEqual(status, 400)
        self.assertIn("expired or was already used", html)

    async def test_get_link_renders_confirmation_form(self):
        token = create_link_token(TEAM_ID, "U123", "C123")

        status, html = await self.get_html(f"{LINK_URL}?t={token}")

        self.assertEqual(status, 200)
        self.assertIn("Connect Slack to Superdesk", html)
        self.assertIn(self.user["username"], html)
        self.assertIn("U123", html)
        self.assertIn(TEAM_ID, html)
        self.assertIn(f'name="t" value="{token}"', html)
        self.assertTrue(nonce_from(html))

    async def test_get_link_when_already_linked_hides_the_form(self):
        await self.links.link(TEAM_ID, "U999", self.user_id, "cli")
        token = create_link_token(TEAM_ID, "U123", "C123")

        status, html = await self.get_html(f"{LINK_URL}?t={token}")

        self.assertEqual(status, 200)
        self.assertIn("already connected to Slack user <strong>U999</strong>", html)
        self.assertNotIn('name="t"', html)

    async def test_post_link_without_nonce(self):
        token = create_link_token(TEAM_ID, "U123", "C123")

        status, html = await self.post_html(LINK_URL, {"t": token})

        self.assertEqual(status, 400)
        self.assertIn("This page has expired.", html)
        self.assertIsNone(await self.links.find_by_slack_user(TEAM_ID, "U123"))

    async def test_post_link_with_wrong_nonce(self):
        token, _ = await self.open_confirm_page()

        status, html = await self.post_html(LINK_URL, {"t": token, "nonce": "not-the-nonce"})

        self.assertEqual(status, 400)
        self.assertIn("This page has expired.", html)
        self.assertIsNone(await self.links.find_by_slack_user(TEAM_ID, "U123"))

    async def test_post_link_creates_the_link(self):
        token, nonce = await self.open_confirm_page()

        status, html = await self.post_html(LINK_URL, {"t": token, "nonce": nonce})

        self.assertEqual(status, 200, html)
        self.assertIn("Connected", html)
        self.assertIn("U123", html)

        link = await self.links.find_by_slack_user(TEAM_ID, "U123")
        assert link is not None
        self.assertEqual(link.user, self.user_id)
        self.assertEqual(link.method, "browser")

        self.notify_slack_user.assert_awaited_once()
        args = self.notify_slack_user.await_args.args
        self.assertEqual(args[0], "C123")
        self.assertEqual(args[1], "U123")
        self.assertIn(self.user["username"], args[2])

    async def test_link_token_cannot_be_used_twice(self):
        token, nonce = await self.open_confirm_page()
        status, _ = await self.post_html(LINK_URL, {"t": token, "nonce": nonce})
        self.assertEqual(status, 200)
        await self.links.unlink_user(self.user_id)

        _, nonce = await self.open_confirm_page()
        status, html = await self.post_html(LINK_URL, {"t": token, "nonce": nonce})

        self.assertEqual(status, 400)
        self.assertIn("expired or was already used", html)

    async def test_post_link_when_slack_user_is_taken(self):
        await self.links.link(TEAM_ID, "U123", ObjectId(), "cli")
        token, nonce = await self.open_confirm_page()

        status, html = await self.post_html(LINK_URL, {"t": token, "nonce": nonce})

        self.assertEqual(status, 409)
        self.assertIn("already connected to another Superdesk account", html)

    async def test_post_link_when_superdesk_user_is_taken(self):
        token, nonce = await self.open_confirm_page()
        await self.links.link(TEAM_ID, "U999", self.user_id, "cli")

        status, html = await self.post_html(LINK_URL, {"t": token, "nonce": nonce})

        self.assertEqual(status, 409)
        self.assertIn("already connected to a different Slack user", html)

    async def test_audit_entry_is_created(self):
        token, nonce = await self.open_confirm_page()
        status, _ = await self.post_html(LINK_URL, {"t": token, "nonce": nonce})
        self.assertEqual(status, 200)

        cursor = await get_resource_service("audit").get_from_mongo_async(
            req=None, lookup={"resource": "slack_user_links"}
        )
        entries = [entry async for entry in cursor]

        # Not asserting a single entry: the audit handler is added to the global signals on every
        # app creation, so a link can be audited more than once when several test apps were built
        self.assertTrue(entries)
        self.assertEqual(entries[0]["action"], "created")
        self.assertEqual(entries[0]["user"], self.user_id)

    async def test_disconnect_without_a_link(self):
        status, html = await self.get_html(DISCONNECT_URL)

        self.assertEqual(status, 200)
        self.assertIn("No Slack account is linked to", html)

    async def test_disconnect_removes_the_link(self):
        await self.links.link(TEAM_ID, "U123", self.user_id, "cli")

        status, html = await self.get_html(DISCONNECT_URL)
        self.assertEqual(status, 200)
        self.assertIn("Disconnect Slack user U123", html)

        status, html = await self.post_html(DISCONNECT_URL, {"nonce": nonce_from(html)})

        self.assertEqual(status, 200)
        self.assertIn("Disconnected", html)
        self.assertIsNone(await self.links.find_by_user(self.user_id))

    async def test_disconnect_post_without_nonce(self):
        await self.links.link(TEAM_ID, "U123", self.user_id, "cli")

        status, html = await self.post_html(DISCONNECT_URL, {})

        self.assertEqual(status, 400)
        self.assertIn("This page has expired.", html)
        self.assertIsNotNone(await self.links.find_by_user(self.user_id))

    async def test_done_page_can_disconnect(self):
        token, nonce = await self.open_confirm_page()
        status, html = await self.post_html(LINK_URL, {"t": token, "nonce": nonce})
        self.assertEqual(status, 200)

        status, html = await self.post_html(DISCONNECT_URL, {"nonce": nonce_from(html)})

        self.assertEqual(status, 200)
        self.assertIn("Disconnected", html)
        self.assertIsNone(await self.links.find_by_user(self.user_id))

    async def test_endpoints_are_inert_without_a_signing_secret(self):
        self.app.config["SLACK_SIGNING_SECRET"] = ""

        response = await self.test_client.get(LINK_URL)
        self.assertEqual(response.status_code, 404)

        response = await self.test_client.get(DISCONNECT_URL)
        self.assertEqual(response.status_code, 404)


class SlackUserLinksServiceTestCase(TestCase):
    app_config = SLACK_CONFIG

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.links = SlackUserLinksService()
        self.user_id = ObjectId()

    async def test_link_is_idempotent_for_the_same_pair(self):
        first = await self.links.link(TEAM_ID, "U123", self.user_id, "cli")
        second = await self.links.link(TEAM_ID, "U123", self.user_id, "cli")

        self.assertEqual(first.id, second.id)
        self.assertEqual(len(await self.links.list_links()), 1)

    async def test_link_accepts_a_string_user_id(self):
        link = await self.links.link(TEAM_ID, "U123", str(self.user_id), "cli")

        self.assertEqual(link.user, self.user_id)
        self.assertIsNotNone(await self.links.find_by_user(str(self.user_id)))

    async def test_link_conflicts(self):
        await self.links.link(TEAM_ID, "U123", self.user_id, "cli")

        with self.assertRaises(SlackLinkConflict) as context:
            await self.links.link(TEAM_ID, "U123", ObjectId(), "cli")
        self.assertEqual(context.exception.reason, "slack_user_linked")

        with self.assertRaises(SlackLinkConflict) as context:
            await self.links.link(TEAM_ID, "U999", self.user_id, "cli")
        self.assertEqual(context.exception.reason, "user_linked")

    async def test_same_slack_user_id_in_another_workspace(self):
        await self.links.link(TEAM_ID, "U123", self.user_id, "cli")
        other = await self.links.link("T999", "U123", ObjectId(), "cli")

        self.assertEqual(other.team_id, "T999")
        self.assertEqual(len(await self.links.list_links()), 2)

    async def test_find_by(self):
        await self.links.link(TEAM_ID, "U123", self.user_id, "browser")

        by_slack_user = await self.links.find_by_slack_user(TEAM_ID, "U123")
        assert by_slack_user is not None
        self.assertEqual(by_slack_user.user, self.user_id)

        by_user = await self.links.find_by_user(self.user_id)
        assert by_user is not None
        self.assertEqual(by_user.slack_user_id, "U123")

        self.assertIsNone(await self.links.find_by_slack_user(TEAM_ID, "U999"))
        self.assertIsNone(await self.links.find_by_user(ObjectId()))

    async def test_unique_indexes(self):
        # The test setup drops the database without recreating the indexes, unlike `app:initialize_data`
        self.app.async_app.mongo.create_indexes_for_all_resources()
        await self.links.link(TEAM_ID, "U123", self.user_id, "cli")

        _, database = self.app.async_app.mongo.get_client("slack_user_links")
        indexes = database["slack_user_links"].index_information()
        self.assertIn("team_id_slack_user_id", indexes)
        self.assertIn("team_id_user", indexes)

        with self.assertRaises(DuplicateKeyError):
            await self.links.mongo_async.insert_one(
                {"team_id": TEAM_ID, "slack_user_id": "U123", "user": ObjectId(), "method": "cli"}
            )

    async def test_unlink(self):
        await self.links.link(TEAM_ID, "U123", self.user_id, "cli")

        self.assertTrue(await self.links.unlink_user(self.user_id))
        self.assertFalse(await self.links.unlink_user(self.user_id))

        await self.links.link(TEAM_ID, "U123", self.user_id, "cli")

        self.assertTrue(await self.links.unlink_slack_user(TEAM_ID, "U123"))
        self.assertFalse(await self.links.unlink_slack_user(TEAM_ID, "U123"))
        self.assertEqual(await self.links.list_links(), [])


class SlackLinkTokenTestCase(TestCase):
    app_config = SLACK_CONFIG

    async def test_create_and_peek(self):
        token = create_link_token(TEAM_ID, "U123", "C123")

        self.assertEqual(
            peek_link_token(token),
            {"team_id": TEAM_ID, "slack_user_id": "U123", "channel": "C123"},
        )
        self.assertIsNotNone(peek_link_token(token))

    async def test_consume_only_works_once(self):
        token = create_link_token(TEAM_ID, "U123")

        self.assertEqual(consume_link_token(token)["channel"], None)
        self.assertIsNone(consume_link_token(token))
        self.assertIsNone(peek_link_token(token))

    async def test_unknown_token(self):
        self.assertIsNone(peek_link_token("nosuchtoken"))
        self.assertIsNone(consume_link_token("nosuchtoken"))

    async def test_link_url(self):
        self.app.config["SERVER_URL"] = "https://superdesk.example.com/api/"

        self.assertEqual(
            get_link_url("abc"),
            "https://superdesk.example.com/api/slack/link?t=abc",
        )

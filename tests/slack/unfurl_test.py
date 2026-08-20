import json
import re

from datetime import timedelta
from unittest import mock

from bson import ObjectId
from slack_sdk.errors import SlackApiError

from superdesk.slack.linking import create_link_token, peek_link_token, pop_pending_unfurl, store_pending_unfurl
from superdesk.slack.resources import SlackUserLinksService
from superdesk.slack.tasks import unfurl_links
from superdesk.tests import TestCase, setup_auth_user
from superdesk.types import UsersResourceModel
from superdesk.utc import utcnow
from tests.entity_preview.fixtures import (
    ADMIN,
    DESK_A,
    DISABLED,
    MEMBER_A,
    OUTSIDER,
    STAGE_A1,
    content_item,
    insert_content_fixtures,
)


CLIENT_URL = "https://news.example.com"
TEAM_ID = "T123"
SLACK_USER = "U123"
CHANNEL = "C123"
MESSAGE_TS = "1700000000.000100"

SLACK_CONFIG = {
    "SLACK_SIGNING_SECRET": "testsecret",
    "SLACK_BOT_TOKEN": "xoxb-test",
    "SLACK_TEAM_ID": TEAM_ID,
    "CLIENT_URL": CLIENT_URL,
}

EMBARGOED_HEADLINE = "Embargoed headline"


def item_url(item_id: str) -> str:
    return f"{CLIENT_URL}/#/workspace?item={item_id}&action=view"


def nonce_from(html: str) -> str:
    match = re.search(r'name="nonce" value="([^"]+)"', html)
    assert match is not None, html
    return match.group(1)


class SlackUnfurlTestCase(TestCase):
    app_config = SLACK_CONFIG

    async def asyncSetUp(self):
        await super().asyncSetUp()

        insert_content_fixtures(self.app)
        self.app.data.insert(
            "archive",
            [
                content_item(
                    "embargoed_a1",
                    ADMIN,
                    headline=EMBARGOED_HEADLINE,
                    embargo=utcnow() + timedelta(hours=2),
                    task={"desk": DESK_A, "stage": STAGE_A1},
                )
            ],
        )

        self.links = SlackUserLinksService()
        self.client = mock.MagicMock()
        self.client.chat_unfurl = mock.AsyncMock()

        patcher = mock.patch("superdesk.slack.tasks.get_slack_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def run_task(
        self,
        links: list[str],
        *,
        slack_user_id: str | None = SLACK_USER,
        channel: str | None = CHANNEL,
        message_ts: str | None = MESSAGE_TS,
        unfurl_id: str | None = None,
        source: str | None = "conversations_history",
        event_id: str | None = "Ev123",
    ) -> None:
        await unfurl_links(
            team_id=TEAM_ID,
            channel=channel,
            message_ts=message_ts,
            thread_ts=None,
            unfurl_id=unfurl_id,
            source=source,
            slack_user_id=slack_user_id,
            links=links,
            event_id=event_id,
        )

    def unfurl_kwargs(self) -> dict:
        self.client.chat_unfurl.assert_awaited_once()
        return self.client.chat_unfurl.await_args.kwargs

    async def test_nothing_is_sent_without_a_bot_token(self):
        with mock.patch("superdesk.slack.tasks.get_slack_client", return_value=None):
            await self.run_task([item_url("item_a1")])

        self.client.chat_unfurl.assert_not_awaited()

    async def test_unsupported_urls_are_ignored(self):
        await self.run_task(
            [
                "https://other.example.com/#/workspace?item=item_a1&action=view",
                f"{CLIENT_URL}/#/planning?item=item_a1",
            ]
        )

        self.client.chat_unfurl.assert_not_awaited()

    async def test_unlinked_user_gets_the_connect_prompt(self):
        links = [item_url("item_a1")]

        await self.run_task(links)

        kwargs = self.unfurl_kwargs()
        self.assertEqual(kwargs["channel"], CHANNEL)
        self.assertEqual(kwargs["ts"], MESSAGE_TS)
        self.assertEqual(kwargs["unfurls"], {})
        self.assertTrue(kwargs["user_auth_required"])
        self.assertIn("Connect your Slack account", kwargs["user_auth_message"])

        prefix = "{}/slack/link?t=".format(self.app.config["SERVER_URL"].rstrip("/"))
        self.assertTrue(kwargs["user_auth_url"].startswith(prefix), kwargs["user_auth_url"])
        self.assertEqual(
            peek_link_token(kwargs["user_auth_url"][len(prefix) :]),
            {"team_id": TEAM_ID, "slack_user_id": SLACK_USER, "channel": CHANNEL},
        )

        pending = pop_pending_unfurl(TEAM_ID, SLACK_USER)
        assert pending is not None
        self.assertEqual(pending["links"], links)
        self.assertEqual(pending["event_id"], "Ev123")
        self.assertEqual(pending["message_ts"], MESSAGE_TS)

    async def test_linked_user_gets_the_full_card(self):
        await self.links.link(TEAM_ID, SLACK_USER, MEMBER_A, "cli")

        await self.run_task([item_url("item_a1")])

        kwargs = self.unfurl_kwargs()
        self.assertNotIn("user_auth_required", kwargs)
        self.assertEqual(list(kwargs["unfurls"]), [item_url("item_a1")])
        self.assertIn("item_a1", json.dumps(kwargs["unfurls"][item_url("item_a1")]["blocks"]))

    async def test_item_the_user_cannot_see_is_not_unfurled(self):
        await self.links.link(TEAM_ID, SLACK_USER, OUTSIDER, "cli")

        await self.run_task([item_url("item_a2")])

        self.client.chat_unfurl.assert_not_awaited()

    async def test_embargoed_item_gets_the_generic_card(self):
        await self.links.link(TEAM_ID, SLACK_USER, MEMBER_A, "cli")

        await self.run_task([item_url("embargoed_a1")])

        blocks = json.dumps(self.unfurl_kwargs()["unfurls"][item_url("embargoed_a1")]["blocks"])
        self.assertIn("Details are restricted", blocks)
        self.assertNotIn(EMBARGOED_HEADLINE, blocks)

    async def test_only_the_visible_url_of_a_mixed_list_is_unfurled(self):
        await self.links.link(TEAM_ID, SLACK_USER, MEMBER_A, "cli")

        await self.run_task(
            [
                item_url("item_a1"),
                item_url("draft_b"),
                "https://other.example.com/#/workspace?item=item_b1&action=view",
            ]
        )

        self.assertEqual(list(self.unfurl_kwargs()["unfurls"]), [item_url("item_a1")])

    async def test_composer_event_is_addressed_by_its_unfurl_id(self):
        await self.links.link(TEAM_ID, SLACK_USER, MEMBER_A, "cli")

        await self.run_task([item_url("item_a1")], message_ts=None, unfurl_id="C123.abc", source="composer")

        kwargs = self.unfurl_kwargs()
        self.assertEqual(kwargs["unfurl_id"], "C123.abc")
        self.assertEqual(kwargs["source"], "composer")
        self.assertNotIn("channel", kwargs)
        self.assertNotIn("ts", kwargs)

    async def test_slack_api_error_does_not_propagate(self):
        await self.links.link(TEAM_ID, SLACK_USER, MEMBER_A, "cli")
        self.client.chat_unfurl.side_effect = SlackApiError("nope", {"ok": False, "error": "cannot_unfurl_url"})

        await self.run_task([item_url("item_a1")])

        self.client.chat_unfurl.assert_awaited_once()

    async def test_disabled_user_sees_nothing(self):
        await self.links.link(TEAM_ID, SLACK_USER, DISABLED, "cli")

        await self.run_task([item_url("item_a1")])

        self.client.chat_unfurl.assert_not_awaited()

    async def test_event_without_a_slack_user_is_dropped(self):
        await self.run_task([item_url("item_a1")], slack_user_id=None)

        self.client.chat_unfurl.assert_not_awaited()


class SlackUnfurlReplayTestCase(TestCase):
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

        notify_patcher = mock.patch("superdesk.slack.views.notify_slack_user", new=mock.AsyncMock())
        self.notify_slack_user = notify_patcher.start()
        self.addCleanup(notify_patcher.stop)

        enqueue_patcher = mock.patch("superdesk.slack.views.enqueue_unfurl", new=mock.AsyncMock())
        self.enqueue_unfurl = enqueue_patcher.start()
        self.addCleanup(enqueue_patcher.stop)

    async def connect(self, slack_user_id: str = SLACK_USER) -> str:
        token = create_link_token(TEAM_ID, slack_user_id, CHANNEL)
        response = await self.test_client.get(f"/api/slack/link?t={token}")
        self.assertEqual(response.status_code, 200)
        nonce = nonce_from(await response.get_data(as_text=True))

        response = await self.test_client.post("/api/slack/link", form={"t": token, "nonce": nonce})
        self.assertEqual(response.status_code, 200)
        return await response.get_data(as_text=True)

    def pending_unfurl(self) -> dict:
        return {
            "team_id": TEAM_ID,
            "channel": CHANNEL,
            "message_ts": MESSAGE_TS,
            "thread_ts": None,
            "unfurl_id": None,
            "source": "conversations_history",
            "slack_user_id": SLACK_USER,
            "links": [item_url("item_a1")],
            "event_id": "Ev123",
        }

    async def test_connecting_replays_the_pending_unfurl(self):
        pending = self.pending_unfurl()
        store_pending_unfurl(TEAM_ID, SLACK_USER, pending)

        await self.connect()

        self.enqueue_unfurl.assert_awaited_once_with(**pending)
        self.assertIsNone(pop_pending_unfurl(TEAM_ID, SLACK_USER))
        self.assertIn("will appear shortly", self.notify_slack_user.await_args.args[2])

    async def test_connecting_without_a_pending_unfurl(self):
        await self.connect()

        self.enqueue_unfurl.assert_not_awaited()
        self.assertIn("Paste the link again", self.notify_slack_user.await_args.args[2])

    async def test_a_failing_replay_does_not_break_the_page(self):
        store_pending_unfurl(TEAM_ID, SLACK_USER, self.pending_unfurl())
        self.enqueue_unfurl.side_effect = RuntimeError("broker is down")

        html = await self.connect()

        self.assertIn("Connected", html)
        self.assertIn("Paste the link again", self.notify_slack_user.await_args.args[2])


class SlackUnfurlUnknownUserTestCase(TestCase):
    """A link pointing at a Superdesk user that no longer exists must not show anything."""

    app_config = SLACK_CONFIG

    async def asyncSetUp(self):
        await super().asyncSetUp()

        insert_content_fixtures(self.app)
        await SlackUserLinksService().link(TEAM_ID, SLACK_USER, ObjectId(), "cli")

        self.client = mock.MagicMock()
        self.client.chat_unfurl = mock.AsyncMock()
        patcher = mock.patch("superdesk.slack.tasks.get_slack_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_unknown_superdesk_user_sees_nothing(self):
        await unfurl_links(
            team_id=TEAM_ID,
            channel=CHANNEL,
            message_ts=MESSAGE_TS,
            thread_ts=None,
            unfurl_id=None,
            source="conversations_history",
            slack_user_id=SLACK_USER,
            links=[item_url("item_a1")],
            event_id="Ev123",
        )

        self.client.chat_unfurl.assert_not_awaited()

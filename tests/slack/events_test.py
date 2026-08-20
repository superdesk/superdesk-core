import hashlib
import hmac
import json
import time
from unittest import mock

from superdesk.tests import AsyncFlaskTestCase


SECRET = "testsecret"
EVENTS_URL = "/api/slack/events"
TEAM_ID = "T123"


def slack_headers(body: bytes, secret: str = SECRET, timestamp: str | None = None) -> dict[str, str]:
    timestamp = timestamp or str(int(time.time()))
    digest = hmac.new(secret.encode(), f"v0:{timestamp}:{body.decode()}".encode(), hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Slack-Signature": f"v0={digest}",
        "X-Slack-Request-Timestamp": timestamp,
    }


def link_shared_payload(event: dict, event_id: str = "Ev123") -> dict:
    return {
        "type": "event_callback",
        "team_id": TEAM_ID,
        "api_app_id": "A123",
        "event_id": event_id,
        "event": {"type": "link_shared", **event},
    }


class SlackEventsTestCase(AsyncFlaskTestCase):
    app_config = {
        "MODULES": ["superdesk.slack"],
        "SLACK_SIGNING_SECRET": SECRET,
        "SLACK_BOT_TOKEN": "xoxb-test",
        "CELERY_TASK_ALWAYS_EAGER": True,
    }

    async def post_signed(self, payload, secret: str = SECRET, timestamp: str | None = None, extra_headers=None):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        headers = slack_headers(body, secret=secret, timestamp=timestamp)
        headers.update(extra_headers or {})
        return await self.test_client.post(EVENTS_URL, data=body, headers=headers)

    async def test_url_verification(self):
        payload = {"type": "url_verification", "challenge": "abc123", "token": "unused"}
        response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"challenge": "abc123"})

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_link_shared_from_message(self, enqueue_unfurl):
        payload = link_shared_payload(
            {
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "source": "conversations_history",
                "user": "U123",
                "links": [
                    {"url": "https://example.com/a", "domain": "example.com"},
                    {"url": "https://example.com/b", "domain": "example.com"},
                ],
            }
        )
        response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Slack-No-Retry"), "1")
        enqueue_unfurl.assert_called_once_with(
            team_id=TEAM_ID,
            channel="C123",
            message_ts="1700000000.000100",
            thread_ts=None,
            unfurl_id=None,
            source="conversations_history",
            slack_user_id="U123",
            links=["https://example.com/a", "https://example.com/b"],
            event_id="Ev123",
        )

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_link_shared_from_composer(self, enqueue_unfurl):
        payload = link_shared_payload(
            {
                "channel": "C123",
                "unfurl_id": "C123.1700000000.000100.abc",
                "source": "composer",
                "user": "U123",
                "links": [{"url": "https://example.com/a", "domain": "example.com"}],
            }
        )
        response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_called_once_with(
            team_id=TEAM_ID,
            channel="C123",
            message_ts=None,
            thread_ts=None,
            unfurl_id="C123.1700000000.000100.abc",
            source="composer",
            slack_user_id="U123",
            links=["https://example.com/a"],
            event_id="Ev123",
        )

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_retry_header_is_still_processed(self, enqueue_unfurl):
        payload = link_shared_payload(
            {
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "source": "conversations_history",
                "user": "U123",
                "links": [{"url": "https://example.com/a"}],
            }
        )
        response = await self.post_signed(payload, extra_headers={"X-Slack-Retry-Num": "2"})

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_called_once()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_tampered_body(self, enqueue_unfurl):
        signed_body = json.dumps({"type": "url_verification", "challenge": "abc123"}).encode()
        headers = slack_headers(signed_body)
        other_body = json.dumps({"type": "url_verification", "challenge": "tampered"}).encode()

        response = await self.test_client.post(EVENTS_URL, data=other_body, headers=headers)

        self.assertEqual(response.status_code, 401)
        enqueue_unfurl.assert_not_called()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_stale_timestamp(self, enqueue_unfurl):
        stale = str(int(time.time()) - 60 * 6)
        response = await self.post_signed({"type": "url_verification", "challenge": "abc"}, timestamp=stale)

        self.assertEqual(response.status_code, 401)
        enqueue_unfurl.assert_not_called()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_missing_signature_headers(self, enqueue_unfurl):
        body = json.dumps({"type": "url_verification", "challenge": "abc"}).encode()
        response = await self.test_client.post(EVENTS_URL, data=body, headers={"Content-Type": "application/json"})

        self.assertEqual(response.status_code, 401)
        enqueue_unfurl.assert_not_called()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_event_from_another_team(self, enqueue_unfurl):
        self.app.config["SLACK_TEAM_ID"] = "TOTHER"
        payload = link_shared_payload(
            {
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "source": "conversations_history",
                "user": "U123",
                "links": [{"url": "https://example.com/a"}],
            }
        )
        response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_not_called()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_event_from_configured_team(self, enqueue_unfurl):
        self.app.config["SLACK_TEAM_ID"] = TEAM_ID
        payload = link_shared_payload(
            {
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "source": "conversations_history",
                "user": "U123",
                "links": [{"url": "https://example.com/a"}],
            }
        )
        response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_called_once()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_event_from_another_app(self, enqueue_unfurl):
        self.app.config["SLACK_APP_ID"] = "AOTHER"
        payload = link_shared_payload(
            {
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "source": "conversations_history",
                "user": "U123",
                "links": [{"url": "https://example.com/a"}],
            }
        )
        response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_not_called()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_other_event_type(self, enqueue_unfurl):
        payload = {
            "type": "event_callback",
            "team_id": TEAM_ID,
            "api_app_id": "A123",
            "event_id": "Ev456",
            "event": {"type": "app_mention", "channel": "C123", "user": "U123"},
        }
        response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_not_called()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_unknown_payload_type(self, enqueue_unfurl):
        response = await self.post_signed({"type": "app_rate_limited", "team_id": TEAM_ID})

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_not_called()

    @mock.patch("superdesk.slack.views.enqueue_unfurl")
    async def test_invalid_json(self, enqueue_unfurl):
        response = await self.post_signed(b"not json at all")

        self.assertEqual(response.status_code, 200)
        enqueue_unfurl.assert_not_called()

    async def test_link_shared_reaches_the_celery_task(self):
        payload = link_shared_payload(
            {
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "source": "conversations_history",
                "user": "U123",
                "links": [{"url": "https://example.com/a"}],
            }
        )
        with mock.patch("superdesk.slack.views.unfurl_links.apply_async", new_callable=mock.AsyncMock) as apply_async:
            response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        apply_async.assert_called_once_with(
            kwargs={
                "team_id": TEAM_ID,
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "thread_ts": None,
                "unfurl_id": None,
                "source": "conversations_history",
                "slack_user_id": "U123",
                "links": ["https://example.com/a"],
                "event_id": "Ev123",
            }
        )

    async def test_celery_task_runs_eagerly(self):
        payload = link_shared_payload(
            {
                "channel": "C123",
                "message_ts": "1700000000.000100",
                "source": "conversations_history",
                "user": "U123",
                "links": [{"url": "https://example.com/a"}],
            }
        )
        # The link is not a Superdesk client URL, so the task stops right after resolving it
        with self.assertLogs("superdesk.slack.tasks", level="DEBUG") as logs:
            response = await self.post_signed(payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn("slack unfurl event_id=Ev123 carries no supported link", logs.output[0])


class SlackNotConfiguredTestCase(AsyncFlaskTestCase):
    app_config = {
        "MODULES": ["superdesk.slack"],
        "SLACK_SIGNING_SECRET": "",
        "SLACK_BOT_TOKEN": "",
        "CELERY_TASK_ALWAYS_EAGER": True,
    }

    async def test_endpoint_returns_404(self):
        body = json.dumps({"type": "url_verification", "challenge": "abc"}).encode()
        response = await self.test_client.post(EVENTS_URL, data=body, headers=slack_headers(body))

        self.assertEqual(response.status_code, 404)
        # An empty body tells the 404 apart from the one Quart returns for an unregistered route
        self.assertEqual(await response.get_data(), b"")

    async def test_endpoint_serves_once_the_secret_is_set(self):
        self.app.config["SLACK_SIGNING_SECRET"] = SECRET
        body = json.dumps({"type": "url_verification", "challenge": "abc"}).encode()
        response = await self.test_client.post(EVENTS_URL, data=body, headers=slack_headers(body))

        self.assertEqual(response.status_code, 200)

import hashlib
import hmac
import time

from superdesk.slack.signature import verify_slack_request
from superdesk.tests import AsyncFlaskTestCase


SECRET = "testsecret"


def sign(body: bytes, secret: str = SECRET, timestamp: str | None = None) -> dict[str, str]:
    timestamp = timestamp or str(int(time.time()))
    digest = hmac.new(secret.encode(), f"v0:{timestamp}:{body.decode()}".encode(), hashlib.sha256).hexdigest()
    return {
        "X-Slack-Signature": f"v0={digest}",
        "X-Slack-Request-Timestamp": timestamp,
    }


class SlackSignatureTestCase(AsyncFlaskTestCase):
    app_config = {
        "MODULES": ["superdesk.slack"],
        "SLACK_SIGNING_SECRET": SECRET,
        "SLACK_BOT_TOKEN": "xoxb-test",
    }

    async def test_valid_signature(self):
        body = b'{"type": "url_verification"}'
        self.assertTrue(verify_slack_request(sign(body), body))

    async def test_signature_from_another_secret(self):
        body = b'{"type": "url_verification"}'
        self.assertFalse(verify_slack_request(sign(body, secret="othersecret"), body))

    async def test_tampered_body(self):
        headers = sign(b'{"type": "url_verification"}')
        self.assertFalse(verify_slack_request(headers, b'{"type": "event_callback"}'))

    async def test_stale_timestamp(self):
        body = b'{"type": "url_verification"}'
        stale = str(int(time.time()) - 60 * 6)
        self.assertFalse(verify_slack_request(sign(body, timestamp=stale), body))

    async def test_malformed_timestamp(self):
        body = b'{"type": "url_verification"}'
        headers = sign(body)
        headers["X-Slack-Request-Timestamp"] = "not-a-timestamp"
        self.assertFalse(verify_slack_request(headers, body))

    async def test_missing_headers(self):
        self.assertFalse(verify_slack_request({}, b'{"type": "url_verification"}'))

    async def test_no_secret_configured(self):
        body = b'{"type": "url_verification"}'
        headers = sign(body)
        self.app.config["SLACK_SIGNING_SECRET"] = ""
        self.assertFalse(verify_slack_request(headers, body))

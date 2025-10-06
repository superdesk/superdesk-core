from superdesk.tests import TestCase
from superdesk.auth.oauth import init_app


class OAuthTestCase(TestCase):
    async def test_oauth_setup(self):
        self.app.config["GOOGLE_CLIENT_ID"] = "test_client_id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test_client_secret"
        self.app.config["GOOGLE_LOGIN"] = True
        init_app(self.app)

        async with self.app.test_client() as client:
            resp = await client.get("/api/login/google")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("accounts.google.com", resp.location)

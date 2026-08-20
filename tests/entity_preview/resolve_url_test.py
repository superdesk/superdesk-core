from superdesk.entity_preview import get_item_url, parse_client_url, resolve_url
from superdesk.entity_preview.content import content_handler
from superdesk.tests import AsyncFlaskTestCase


CLIENT_URL = "https://news.example.com"
ITEM_ID = "urn:newsml:localhost:2024-01-01T00:00:00.000000:abc"


class ResolveUrlTestCase(AsyncFlaskTestCase):
    app_config = {"CLIENT_URL": CLIENT_URL}

    def assertResolves(self, url: str, item_id: str = ITEM_ID):
        ref = resolve_url(url)
        self.assertIsNotNone(ref, url)
        assert ref is not None
        self.assertEqual("content", ref.type)
        self.assertEqual(item_id, ref.id)

    def assertNoMatch(self, url: str):
        self.assertIsNone(resolve_url(url), url)

    async def test_workspace_item_url(self):
        self.assertResolves(f"{CLIENT_URL}/#/workspace?item={ITEM_ID}&action=view")

    async def test_workspace_item_url_with_extra_args(self):
        self.assertResolves(f"{CLIENT_URL}/#/workspace?item={ITEM_ID}&action=edit&comments=123")

    async def test_personal_workspace(self):
        self.assertResolves(f"{CLIENT_URL}/#/workspace/personal?item={ITEM_ID}&action=edit")

    async def test_monitoring_with_valueless_arg(self):
        self.assertResolves(f"{CLIENT_URL}/#/workspace/monitoring?item={ITEM_ID}&action=view&popup")

    async def test_search(self):
        self.assertResolves(f"{CLIENT_URL}/#/search?item={ITEM_ID}&action=view")

    async def test_legacy_authoring_url_uses_id_arg(self):
        self.assertResolves(f"{CLIENT_URL}/#/authoring/{ITEM_ID}?_id={ITEM_ID}")

    async def test_legacy_authoring_url_without_id_arg(self):
        self.assertResolves(f"{CLIENT_URL}/#/authoring/{ITEM_ID}")

    async def test_percent_encoded_id_is_decoded(self):
        encoded = ITEM_ID.replace(":", "%3A")
        self.assertResolves(f"{CLIENT_URL}/#/workspace?item={encoded}&action=view")

    async def test_http_and_https_are_both_accepted(self):
        self.assertResolves(f"http://news.example.com/#/workspace?item={ITEM_ID}&action=view")

    async def test_trailing_slash_before_fragment(self):
        self.assertResolves(f"{CLIENT_URL}/#/workspace/?item={ITEM_ID}&action=view")

    async def test_other_host(self):
        self.assertNoMatch(f"https://other.example.com/#/workspace?item={ITEM_ID}&action=view")

    async def test_subdomain_is_not_a_match(self):
        self.assertNoMatch(f"https://a.news.example.com/#/workspace?item={ITEM_ID}&action=view")

    async def test_explicit_port_is_part_of_the_host(self):
        self.assertNoMatch(f"https://news.example.com:8443/#/workspace?item={ITEM_ID}&action=view")

    async def test_non_http_scheme(self):
        self.assertNoMatch(f"ftp://news.example.com/#/workspace?item={ITEM_ID}&action=view")

    async def test_planning_is_not_content(self):
        self.assertNoMatch(f"{CLIENT_URL}/#/planning?preview=%7B%22id%22%3A%22plan%22%7D")

    async def test_assignments_are_not_content(self):
        self.assertNoMatch(f"{CLIENT_URL}/#/workspace/assignments?assignment=abc123")

    async def test_monitoring_without_item(self):
        self.assertNoMatch(f"{CLIENT_URL}/#/workspace/monitoring")

    async def test_url_without_fragment(self):
        self.assertNoMatch(f"{CLIENT_URL}/workspace?item={ITEM_ID}")

    async def test_fragment_not_starting_with_slash(self):
        self.assertNoMatch(f"{CLIENT_URL}/#workspace?item={ITEM_ID}")

    async def test_garbage(self):
        for url in ["", "not a url", "https://", "#/workspace?item=x", "https://news.example.com"]:
            self.assertNoMatch(url)

    async def test_parse_client_url_keeps_first_value_of_repeated_keys(self):
        parsed = parse_client_url(f"{CLIENT_URL}/#/workspace?item=first&item=second&action=view")
        assert parsed is not None
        self.assertEqual("news.example.com", parsed.host)
        self.assertEqual("/workspace", parsed.path)
        self.assertEqual({"item": "first", "action": "view"}, parsed.query)

    async def test_canonical_url(self):
        expected = f"{CLIENT_URL}/#/workspace?item={ITEM_ID}&action=view"
        self.assertEqual(expected, get_item_url(ITEM_ID))
        self.assertEqual(expected, content_handler.canonical_url(ITEM_ID))

    async def test_canonical_url_strips_trailing_slash_from_client_url(self):
        self.app.config["CLIENT_URL"] = "https://news.example.com/"
        self.assertEqual(f"{CLIENT_URL}/#/workspace?item=x&action=view", get_item_url("x"))

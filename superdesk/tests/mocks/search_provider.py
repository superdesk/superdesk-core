from superdesk import SearchProvider, register_search_provider
from superdesk.utils import ListCursor
from superdesk.errors import SuperdeskApiError
from apps.search_providers import allowed_search_providers


FIXTURES = [
    {
        "type": "text",
        "mimetype": "application/superdesk.item.text",
        "pubstatus": "usable",
        "_id": "urn:localhost:sofab:english-abcd123",
        "guid": "urn:localhost:sofab:english-abcd123",
        "headline": "Test English Headline",
        "slugline": "test-slugline",
        "body_html": "<p>Test English body</p>",
        "versioncreated": "2024-03-20T15:27:15Z",
        "firstcreated": "2024-03-20T15:27:15Z",
        "source": "sofab",
        "language": "en",
        "word_count": 3,
        "_fetchable": False,
    },
    {
        "type": "text",
        "mimetype": "application/superdesk.item.text",
        "pubstatus": "usable",
        "_id": "urn:localhost:sofab:deutsch-abcd123",
        "guid": "urn:localhost:sofab:deutsch-abcd123",
        "headline": "Test Deutsch Headline",
        "slugline": "test-slugline",
        "body_html": "<p>Test Deutsch body</p>",
        "versioncreated": "2024-03-20T15:27:15Z",
        "firstcreated": "2024-03-20T15:27:15Z",
        "source": "sofab",
        "language": "de",
        "word_count": 3,
        "_fetchable": False,
    },
    {
        "type": "text",
        "mimetype": "application/superdesk.item.text",
        "pubstatus": "usable",
        "_id": "urn:localhost:sofab:deutsch-abcd123-2",
        "guid": "urn:localhost:sofab:deutsch-abcd123-2",
        "headline": "Test Deutsch Headline 2",
        "slugline": "test-slugline",
        "body_html": "<p>Test Deutsch body 2</p>",
        "versioncreated": "2024-03-20T15:27:15Z",
        "firstcreated": "2024-03-20T15:27:15Z",
        "source": "sofab",
        "language": "de",
        "word_count": 4,
        "_fetchable": False,
    },
    {
        "type": "text",
        "mimetype": "application/superdesk.item.text",
        "pubstatus": "usable",
        "_id": "urn:localhost:sofab:french-abcd123",
        "guid": "urn:localhost:sofab:french-abcd123",
        "headline": "Test French Headline",
        "slugline": "test-slugline",
        "body_html": "<p>Test French body</p>",
        "versioncreated": "2024-03-20T15:27:15Z",
        "firstcreated": "2024-03-20T15:27:15Z",
        "source": "sofab",
        "language": "fr",
        "word_count": 3,
        "_fetchable": False,
    }
]


class TestSearchProvider(SearchProvider):
    label = "Test Search Provider"

    def find(self, query):
        return ListCursor(FIXTURES)

    def fetch(self, guid):
        item = next(
            (
                item
                for item in FIXTURES
                if item.get("_id") == guid
            ),
            None
        )
        if item is None:
            raise SuperdeskApiError.notFoundError("Search item not found")
        return item


def init_app(_app):
    if "TestSearchProvider" not in allowed_search_providers:
        register_search_provider("TestSearchProvider", provider_class=TestSearchProvider)

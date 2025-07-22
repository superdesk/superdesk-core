from flask import json
from eve.utils import ParsedRequest

from superdesk import SearchProvider, register_search_provider, get_resource_service
from superdesk.errors import SuperdeskApiError
from apps.search_providers import allowed_search_providers
from apps.archive.common import ARCHIVE


class TestSearchProvider(SearchProvider):
    label = "Test Search Provider"

    def find(self, query):
        request = ParsedRequest()
        request.args = {"source": json.dumps(query), "repo": "archive,published"}
        return get_resource_service("search").get(req=request, lookup=None)

    def fetch(self, guid):
        item = get_resource_service(ARCHIVE).find_one(req=None, _id=guid)

        if item is None:
            raise SuperdeskApiError.notFoundError("Search item not found")
        return item


def init_app(_app):
    if "TestSearchProvider" not in allowed_search_providers:
        register_search_provider("TestSearchProvider", provider_class=TestSearchProvider)

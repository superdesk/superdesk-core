from superdesk import SearchProvider


class TestSearchProvider(SearchProvider):
    label = "Foo"

    async def find_async(self, query):
        return [{"guid": "foo", "source": "bar"}]

    async def fetch_async(self, guid):
        return {"_id": guid, "headline": guid, "source": "bar"}

    def fetch_file(self, href):
        return {"href": href}

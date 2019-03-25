
from superdesk import SearchProvider


class TestSearchProvider(SearchProvider):

    label = 'Foo'

    def find(self, query):
        return [{'guid': 'foo', 'source': 'bar'}]

    def fetch(self, guid):
        return {'_id': guid, 'headline': guid, 'source': 'bar'}

    def fetch_file(self, href):
        return {'href': href}

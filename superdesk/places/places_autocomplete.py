import superdesk

from superdesk.utils import ListCursor
from superdesk.geonames import geonames_request, format_geoname_item


class PlacesAutocompleteResource(superdesk.Resource):

    resource_methods = ['GET']
    item_methods = []


class PlacesAutocompleteService(superdesk.Service):
    def get(self, req, lookup):
        assert req.args.get('name'), {'name': 1}
        params = [
            ('name_startsWith', req.args.get('name')),
            ('lang', req.args.get('lang')),
            ('featureClass', 'A'),
            ('featureClass', 'P'),
        ]

        json_data = geonames_request('search', params)
        data = [format_geoname_item(item) for item in json_data.get('geonames', [])]
        return ListCursor(data)

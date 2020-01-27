import superdesk

from flask import current_app as app
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
            ('style', req.args.get('style', app.config['GEONAMES_SEARCH_STYLE'])),
        ]

        if req.args.get('featureClass'):
            params.append(('featureClass', req.args.get('featureClass')))
        else:
            for feature_class in app.config['GEONAMES_FEATURE_CLASSES']:
                params.append(('featureClass', feature_class.upper()))

        json_data = geonames_request('search', params)
        data = [format_geoname_item(item) for item in json_data.get('geonames', [])]
        return ListCursor(data)

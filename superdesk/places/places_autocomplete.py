import logging
import requests
import superdesk

from urllib.parse import urljoin
from flask import current_app as app
from superdesk.utils import ListCursor

logger = logging.getLogger(__name__)


def format_geoname_item(item):
    return {
        'scheme': 'geonames',
        'code': str(item['geonameId']),
        'name': item['name'],
        'state': item.get('adminName1'),
        'country': item.get('countryName'),
        'state_code': item.get('adminCodes1', {}).get('ISO3166_2'),
        'country_code': item.get('countryCode'),
        'feature_class': item.get('fcl'),
        'location': {
            'lat': float(item['lat']),
            'lon': float(item['lng']),
        }
    }


def geonames_request(service, service_params):
    params = [
        ('type', 'json'),
        ('username', app.config.get('GEONAMES_USERNAME', '')),
    ]
    params.extend(service_params)
    url = urljoin(app.config.get('GEONAMES_URL', 'http://api.geonames.org/'), service)
    res = requests.get(url, params)
    if res.status_code != 200:
        res.raise_for_status()
    data = res.json()
    return [format_geoname_item(item) for item in data.get('geonames', [])]


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

        data = geonames_request('search', params)
        return ListCursor(data)

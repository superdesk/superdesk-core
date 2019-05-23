"""Geonames utils."""

import requests

from urllib.parse import urljoin
from urllib3.util.retry import Retry

from flask import current_app as app

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.1)
adapter = requests.adapters.HTTPAdapter(max_retries=retries)
session.mount('http://', adapter)
session.mount('https://', adapter)


def get_geonames_state_qcode(place):
    return 'iso3166-2:%s-%s' % (place.get('country_code'), place.get('state_code'))


def get_geonames_country_qcode(place):
    return 'iso3166-1a2:%s' % place.get('country_code')


def get_geonames_qcode(place):
    if place.get('feature_class', '').upper() == 'A':
        if place.get('state_code'):  # state
            return get_geonames_state_qcode(place)
        else:  # country
            return get_geonames_country_qcode(place)
    return 'geonames:%s' % place.get('code', '0')


def format_geoname_item(item):
    geo = {
        'scheme': 'geonames',
        'code': str(item['geonameId']),
        'name': item['name'],
        'state': item.get('adminName1'),
        'region': item.get('adminName2'),
        'country': item.get('countryName'),
        'state_code': item.get('adminCode1'),
        'region_code': item.get('adminCode2'),
        'country_code': item.get('countryCode'),
        'continent_code': item.get('continentCode'),
        'feature_class': item.get('fcl'),
        'location': {
            'lat': float(item['lat']),
            'lon': float(item['lng']),
        }
    }

    if item.get('timezone'):
        geo['tz'] = item['timezone'].get('timeZoneId')

    return geo


def geonames_request(service, service_params):
    params = [
        ('type', 'json'),
        ('username', app.config.get('GEONAMES_USERNAME', '')),
    ]

    if app.config.get('GEONAMES_TOKEN'):
        params.append(('token', app.config['GEONAMES_TOKEN']))

    params.extend(service_params)
    url = urljoin(app.config['GEONAMES_URL'], service)
    res = session.get(url, params=params, timeout=10)
    if res.status_code != 200:
        res.raise_for_status()
    return res.json()

"""Geonames utils."""


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

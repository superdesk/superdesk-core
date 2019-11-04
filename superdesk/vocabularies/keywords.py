
from superdesk import get_resource_service


def add_missing_keywords(sender, item, **kwargs):
    if item.get('keywords'):
        get_resource_service('vocabularies').add_missing_keywords(item['keywords'], item.get('language'))

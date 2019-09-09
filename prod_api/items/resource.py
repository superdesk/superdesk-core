from superdesk.resource import Resource
from superdesk.metadata.utils import item_url


class ItemsResource(Resource):
    url = 'items'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'archive',
        'search_backend': 'elastic',
        'default_sort': [('_updated', -1)]
    }

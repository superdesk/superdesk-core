from superdesk.resource import Resource
from superdesk.metadata.utils import item_url


class ContactsResource(Resource):
    url = 'contacts'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'contacts',
        'search_backend': 'elastic',
        'default_sort': [('last_name', 1)],
        'projection': {
            'fields_meta': 0
        },
    }

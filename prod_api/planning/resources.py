from superdesk.resource import Resource
from superdesk.metadata.utils import item_url


class PlanningResource(Resource):
    url = 'planning'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'planning',
        'search_backend': 'elastic',
        'default_sort': [('_updated', -1)],
        'projection': {
            'fields_meta': 0
        },
    }


class EventsResource(Resource):
    url = 'events'
    item_url = item_url
    item_methods = ['GET']
    resource_methods = ['GET']
    datasource = {
        'source': 'events',
        'search_backend': 'elastic',
        'default_sort': [('dates.start', 1)],
        'projection': {
            'fields_meta': 0
        },
    }

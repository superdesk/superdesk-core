
import superdesk

from flask import current_app as app
from superdesk.utils import ListCursor


class ClientConfigResource(superdesk.Resource):
    item_methods = []
    public_methods = ['GET']
    resource_methods = ['GET']


class ClientConfigService(superdesk.Service):

    def get(self, req, lookup):
        return ListCursor()

    def on_fetched(self, docs):
        docs['config'] = getattr(app, 'client_config', {})


def init_app(app):
    superdesk.register_resource('client_config', ClientConfigResource, ClientConfigService, _app=app)

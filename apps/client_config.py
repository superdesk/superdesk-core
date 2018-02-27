
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
    app.client_config.update({
        'schema': app.config.get('SCHEMA'),
        'editor': app.config.get('EDITOR'),
        'feedback_url': app.config.get('FEEDBACK_URL'),
        'override_ednote_for_corrections': app.config.get('OVERRIDE_EDNOTE_FOR_CORRECTIONS', True),
        'override_ednote_template': app.config.get('OVERRIDE_EDNOTE_TEMPLATE'),
        'default_genre': app.config.get('DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES'),
    })

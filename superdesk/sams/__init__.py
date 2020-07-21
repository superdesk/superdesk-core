import superdesk
from .storage_destinations import destinations_bp
from .sets import sets_bp
from .decorator import blueprint_auth
from sams_client import SamsClient


def init_app(app):

    configs = {
        'HOST': app.config.get('SAMS_HOST'),
        'PORT': app.config.get('SAMS_PORT')
    }
    client = SamsClient(configs)

    @destinations_bp.before_request
    @blueprint_auth(app)
    def before_request():
        """ Add authentication before request to destinations blueprint """
        pass
    superdesk.blueprint(destinations_bp, app, client=client)

    @sets_bp.before_request
    @blueprint_auth(app)
    def before_request():
        """ Add authentication before request to sets blueprint """
        pass
    superdesk.blueprint(sets_bp, app, client=client)

import superdesk
from .storage_destinations import destinations_bp
from .sets import sets_bp
from superdesk.auth.decorator import blueprint_auth
from flask_babel import _
from sams_client import SamsClient


def init_app(app):

    configs = {
        'HOST': app.config.get('SAMS_HOST'),
        'PORT': app.config.get('SAMS_PORT')
    }
    client = SamsClient(configs)

    @destinations_bp.before_request
    @sets_bp.before_request
    @blueprint_auth()
    def before_request():
        """
        Add authentication before request to all blueprint
        """
        pass

    @destinations_bp.after_request
    @sets_bp.after_request
    def after_request(response):
        response.headers.set('Access-Control-Allow-Origin', '*')
        response.headers.set('Access-Control-Allow-Headers', '*')
        response.headers.set('Access-Control-Allow-Methods', '*')
        return response

    superdesk.blueprint(destinations_bp, app, client=client)
    superdesk.blueprint(sets_bp, app, client=client)

    superdesk.privilege(
        name='sams',
        label=_('Sams'),
        description=_(
            'Access to the SAMS management page (and to upload assets etc)'
        )
    )

    superdesk.privilege(
        name='sams_manage',
        label=_('Sams manage'),
        description=_('Allows management of SAMS Sets etc')
    )

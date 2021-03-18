import superdesk
from eve.flaskapp import Eve
from .assets import assets_bp, unlock_asset_by_user
from .storage_destinations import destinations_bp
from .sets import sets_bp
from superdesk.auth.decorator import blueprint_auth
from flask_babel import _
from .client import get_sams_client


def init_app(app: Eve):
    client = get_sams_client(app)

    app.on_session_end -= unlock_assets_on_logout
    app.on_session_end += unlock_assets_on_logout

    @assets_bp.before_request
    @destinations_bp.before_request
    @sets_bp.before_request
    @blueprint_auth()
    def before_request():
        """
        Add authentication before request to all blueprint
        """
        pass

    @assets_bp.after_request
    @destinations_bp.after_request
    @sets_bp.after_request
    def after_request(response):
        response.headers.set("Access-Control-Allow-Origin", "*")
        response.headers.set("Access-Control-Allow-Headers", "*")
        response.headers.set("Access-Control-Allow-Methods", "*")
        return response

    superdesk.blueprint(destinations_bp, app, client=client)
    superdesk.blueprint(sets_bp, app, client=client)
    superdesk.blueprint(assets_bp, app, client=client)

    superdesk.privilege(
        name="sams", label=_("Sams"), description=_("Access to the SAMS management page (and to upload assets etc)")
    )

    superdesk.privilege(name="sams_manage", label=_("Sams manage"), description=_("Allows management of SAMS Sets etc"))

    superdesk.privilege(
        name="sams_manage_assets", label=_("SAMS Manage Assets"), description=_("Allows management of SAMS Assets")
    )


def unlock_assets_on_logout(user_id, session_id):
    unlock_asset_by_user(user_id, session_id)

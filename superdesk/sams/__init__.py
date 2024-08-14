import superdesk
from eve.flaskapp import Eve
from .assets import assets_bp, unlock_asset_by_user
from .storage_destinations import destinations_bp
from .sets import sets_bp
from superdesk.auth.decorator import blueprint_auth
from superdesk.default_settings import RENDITIONS
from quart_babel import gettext as _
from .client import get_sams_client


def init_app(app: Eve):
    client = get_sams_client()

    if not app.config["RENDITIONS"].get("sams"):
        # if SAMS renditions are not defined, then copy them from default settings
        app.config["RENDITIONS"]["sams"] = RENDITIONS["sams"]

        # And re-apply client_config to include SAMS renditions
        app.client_config.setdefault("media", {}).update({"renditions": app.config.get("RENDITIONS")})

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
        response.headers.set("Access-Control-Allow-Origin", app.config["CLIENT_URL"])
        response.headers.set("Access-Control-Allow-Headers", ",".join(app.config["X_HEADERS"]))
        response.headers.set("Access-Control-Allow-Methods", "OPTIONS, PATCH, DELETE, HEAD, PUT, GET, POST")
        response.headers.set("Access-Control-Allow-Credentials", "true")
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


def unlock_assets_on_logout(user_id, session_id, is_last_session):
    unlock_asset_by_user(user_id, session_id)

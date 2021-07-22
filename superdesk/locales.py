import pytz
import flask
import babel.dates as dates

from apps.auth import get_user
from eve.render import send_response


bp = flask.Blueprint("locales", __name__)


def get_timezones():
    user = get_user()
    lang = user.get("language", flask.current_app.config.get("DEFAULT_LANGUAGE", "en")).replace("-", "_")
    return [
        {
            "id": tz,
            "name": dates.get_timezone_name(tz, locale=lang),
            "location": dates.get_timezone_location(tz, locale=lang),
        }
        for tz in pytz.common_timezones
    ]


@bp.route("/locales/timezones", methods=["GET", "OPTIONS"])
def locales_view():
    if not flask.current_app.auth.authorized([], "locales", "GET"):
        flask.abort(401)
    resp = None
    if flask.request.method == "GET":
        resp = {"timezones": get_timezones()}
    return send_response(None, (resp, None, None, 200))


def init_app(app) -> None:
    bp.url_prefix = "/{}".format(app.config["URL_PREFIX"].lstrip("/"))
    app.register_blueprint(bp)

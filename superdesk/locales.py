
import pytz
import flask
import babel.dates as dates

from apps.auth import get_user


bp = flask.Blueprint('locales', __name__)


@bp.route('/locales/timezones')
def locales_view():
    if not flask.current_app.auth.authorized([], 'locales', 'GET'):
        flask.abort(401)
    user = get_user()
    lang = user.get('language', flask.current_app.config.get('DEFAULT_LANGUAGE', 'en')).replace('-', '_')
    return flask.jsonify({
        'timezones': [
            {
                'id': tz,
                'name': dates.get_timezone_name(tz, locale=lang),
                'location': dates.get_timezone_location(tz, locale=lang),
            } for tz in pytz.common_timezones
        ]
    })


def init_app(app):
    bp.url_prefix = '/{}'.format(app.config['URL_PREFIX'].lstrip('/'))
    app.register_blueprint(bp)

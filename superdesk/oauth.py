import superdesk

from flask import url_for, request, render_template, session
from flask_oauthlib.client import OAuth

from apps.auth.auth import AuthResource
from apps.auth.service import AuthService


TEMPLATE = 'oauth_authorized.html'


class OAuthService(AuthService):

    def authenticate(self, document):
        if not document.get('email'):
            return
        return superdesk.get_resource_service('auth_users').find_one(req=None, email=document.get('email'))


class OAuthResource(AuthResource):
    internal_resource = True


def configure_oauth(app):
    superdesk.register_resource('oauth', OAuthResource, OAuthService)
    oauth = OAuth(app)
    app.client_config['google_auth'] = False
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        configure_google(app, oauth)
        app.client_config['google_auth'] = True


def configure_google(app, oauth):

    google = oauth.remote_app(
        'google',
        consumer_key=app.config.get('GOOGLE_CLIENT_ID'),
        consumer_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        request_token_params={'scope': 'email'},

        base_url='https://www.googleapis.com/oauth2/v1/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
    )

    @app.route('/login/google')
    def google_login():
        return google.authorize(callback=url_for('google_authorized', _external=True))

    @app.route('/login/google_authorized')
    def google_authorized():
        resp = google.authorized_response()
        if resp is None:
            return render_template(TEMPLATE, data=request.args)
        try:
            session['google_token'] = (resp['access_token'], '')
            me = google.get('userinfo')
            data = [{'email': me.data['email']}]
            superdesk.get_resource_service('oauth').post(data)
            data[0]['_id'] = str(data[0]['_id'])
            data[0]['user'] = str(data[0]['user'])
            return render_template(TEMPLATE, data=data[0])
        except ValueError:
            return render_template(TEMPLATE, data={'error': 404})

    @google.tokengetter
    def get_google_oauth_token():
        return session.get('google_token')

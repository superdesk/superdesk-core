"""
Superdesk Google Authentication

.. versionadded:: 1.8

You can use Google for authentication, first you have to create credentials
in `Google API console <https://console.developers.google.com/apis/credentials>`_:

- set your client URL as *Authorized JavaScript origins*::

    https://example.com

- set server URL + ``/api/login/google_authorized`` as *Authorized redirect URIs*::

    https://example.com/api/login/google_authorized

Once configured you will find there *Client ID* and *Client secret*, use both to populate :ref:`settings.google_oauth`.

.. versionchanged:: 1.9
    There is no need to configure client, it reads config from server now.

.. versionchanged:: 1.9
    Login url is ``/api/login/google_authorized`` instead of ``/login/google_authorized``.

"""

import superdesk

from flask import url_for, session
from flask_oauthlib.client import OAuth

from superdesk.auth import auth_user


bp = superdesk.Blueprint('oauth', __name__)


def init_app(app):
    oauth = OAuth(app)
    app.client_config['google_auth'] = False
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        app.client_config['google_auth'] = True
        configure_google(app, oauth)
        superdesk.blueprint(bp, app)


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

    @bp.route('/login/google')
    def google_login():
        return google.authorize(callback=url_for('oauth.google_authorized', _external=True))

    @bp.route('/login/google_authorized')
    def google_authorized():
        resp = google.authorized_response()
        if resp is None:
            return auth_user()
        session['google_token'] = (resp['access_token'], '')
        me = google.get('userinfo')
        return auth_user(me.data['email'])

    @google.tokengetter
    def get_google_oauth_token():
        return session.get('google_token')

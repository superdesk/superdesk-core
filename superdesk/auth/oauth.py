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

import logging
from datetime import datetime
from typing import Optional, List
import superdesk
from flask import url_for, render_template
from authlib.integrations.flask_client import OAuth
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc6749.wrappers import OAuth2Token
from superdesk.resource import Resource
from superdesk.services import BaseService

from superdesk.auth import auth_user, TEMPLATE


logger = logging.getLogger(__name__)

bp = superdesk.Blueprint("oauth", __name__)
oauth: Optional[OAuth] = None
REFRESH_TOKEN_URL = "https://oauth2.googleapis.com/token"


def init_app(app) -> None:
    global oauth
    oauth = OAuth(app)

    endpoint_name = "oauth2_token"
    service = OAuth2TokenService(endpoint_name, backend=superdesk.get_backend())
    OAuth2TokenResource(endpoint_name, app=app, service=service)

    app.client_config["google_auth"] = False
    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        app.client_config["google_auth"] = bool(app.config.get("GOOGLE_LOGIN"))
        if app.config.get("GOOGLE_GMAIL"):
            extra_scopes = ["https://mail.google.com"]
            refresh = True
        else:
            extra_scopes = []
            refresh = False

        configure_google(app, extra_scopes=extra_scopes, refresh=refresh)


class OAuth2TokenResource(Resource):
    schema = {
        "name": {
            "type": "string",
            "required": True,
            "nullable": False,
            "empty": False,
        },
        "email": {
            "type": "string",
        },
        "access_token": {
            "type": "string",
            "required": True,
            "nullable": False,
            "empty": False,
        },
        "refresh_token": {
            "type": "string",
        },
        "expires_at": {"type": "datetime"},
    }
    internal_resource = True


class OAuth2TokenService(BaseService):
    """Store OAuth tokens"""


def token2dict(
    token_id: str,
    email: str,
    token: OAuth2Token,
    name: str = "google",
) -> dict:
    """Convert authlib's OAuth2Token to a dict usable with datalayer

    :param token_id: used to associate the token with a provider
    :param email: email associated with this token
    :param token: token to convert
    :param name: name of the OAuth2 service
    """
    return {
        "_id": token_id,
        "name": "google",
        "email": email,
        "access_token": token["access_token"],
        "refresh_token": token.get("refresh_token"),
        "expires_at": datetime.fromtimestamp(token["expires_at"]),
    }


def configure_google(app, extra_scopes: Optional[List[str]] = None, refresh: bool = False) -> None:
    scopes = ["openid", "email", "profile"]
    token_url_id_queue = []
    if extra_scopes:
        scopes.extend(extra_scopes)
    kwargs = {}
    if refresh:
        kwargs["authorize_params"] = {"access_type": "offline"}

    oauth.register(  # type: ignore # mypy seems confused with this global oauth
        "google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": " ".join(scopes)},
        **kwargs,
    )

    @bp.route("/login/google")
    @bp.route("/login/google/<url_id>")
    def google_login(url_id=None):
        """Redirect to google OAuth authorization page

        :param url_id: used to identify the token
            if OAuth is used for Superdesk login, url_id is None.
            Otherwise, it is used to associate the token with the provider needing it
        """
        token_url_id_queue.append(url_id)
        redirect_uri = url_for(".google_authorized", _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    @bp.route("/login/google_authorized")
    def google_authorized():
        token_id = token_url_id_queue.pop() if token_url_id_queue else None
        token = oauth.google.authorize_access_token()
        if not token:
            return render_template(TEMPLATE, data={}) if token_id else auth_user()
        user = oauth.google.parse_id_token(token)
        if token_id:
            # token_id is used to link token with provider, we need to store the token
            # in this case, to be able to use it and refresh later without user interaction
            oauth2_token_service = superdesk.get_resource_service("oauth2_token")
            if token.get("refresh_token"):
                oauth2_token_service.post([token2dict(token_id, user["email"], token)])
            else:
                # we have no refresh_token, that probably means that's it not the first time that we log in
                # with OAuth (refresh token is only returned on first token exchange). We should already have
                # a token in database, let's check it.
                current_token = oauth2_token_service.find_one(req=None, _id=token_id)
                if current_token:
                    if current_token["access_token"] != token["access_token"]:
                        # we have a new access_token, we update it, but we want to keep existing refresh_token
                        token_dict = token2dict(token_id, user["email"], token)
                        oauth2_token_service.update(
                            token_id,
                            {"access_token": token_dict["access_token"], "expires_at": token_dict["expires_at"]},
                            current_token,
                        )
                else:
                    logger.warning(
                        "No refresh token received, that probably means that it's not the first time login is "
                        "requested. Please remove granted permission to Superdesk in Google settings (under "
                        '"security/Third-party apps with account access") then try to log-in again'
                    )

            return render_template(TEMPLATE, data={})
        else:
            # no token_id, OAuth is only used for log-in
            return auth_user(user["email"], {"needs_activation": False})

    superdesk.blueprint(bp, app)


def refresh_google_token(token_id: str) -> dict:
    oauth2_token_service = superdesk.get_resource_service("oauth2_token")
    token = oauth2_token_service.find_one(req=None, _id=token_id)
    if token is None:
        raise ValueError("unknown token id: {_id}".format(_id=token_id))
    if not token["refresh_token"]:
        raise ValueError("missing refresh token for token {_id}".format(_id=token["_id"]))
    session = OAuth2Session(
        oauth.google.client_id,  # type: ignore # mypy seems confused with this global oauth
        oauth.google.client_secret,  # type: ignore
    )
    new_token = session.refresh_token(REFRESH_TOKEN_URL, token["refresh_token"])
    token_dict = token2dict(token["_id"], token["email"], new_token)
    oauth2_token_service.update(token["_id"], token_dict, token)
    return token_dict

"""
Superdesk SAML Authentication

.. versionadded:: 1.9

Configuration
~~~~~~~~~~~~~

To enable SAML auth module, add ``superdesk.auth.saml`` into :ref:`settings.installed_apps` in settings.
Setting :ref:`settings.secret_key` is also required.

Finally you have to specify :ref:`settings.saml_path` in settings where your ``settings.json`` file and
``certs`` are located. See https://github.com/onelogin/python3-saml#how-it-works for more info.

Service provider config for superdesk in ``settings.json`` file example::

    "sp": {
        "entityId": "http://example.com/api/login/saml_metadata",
        "assertionConsumerService": {
            "url": "http://example.com/api/login/saml?acs",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        },
        "singleLogoutService": {
            "url": "http://example.com/api/login/saml?sls",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        "x509cert": "",
        "privateKey": ""
    }

"""

import superdesk
import logging

from urllib.parse import urlparse

from flask import current_app as app, request, redirect, make_response, session, jsonify, json
from superdesk.auth import auth_user

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    imported = True
except ImportError:
    imported = False


SESSION_NAME_ID = "samlNameId"
SESSION_SESSION_ID = "samlSessionIndex"
SESSION_USERDATA_KEY = "samlUserdata"

bp = superdesk.Blueprint("saml", __name__)
logger = logging.getLogger(__name__)


def init_app(app) -> None:
    app.client_config["saml_auth"] = False
    if app.config.get("SAML_PATH"):
        assert imported, "onelogin module is not available"
        app.client_config["saml_auth"] = True
        app.client_config["saml_label"] = app.config["SAML_LABEL"]
        superdesk.blueprint(bp, app)


def init_saml_auth(req):
    auth = OneLogin_Saml2_Auth(req, custom_base_path=app.config["SAML_PATH"])
    return auth


def prepare_flask_request(request):
    url_data = urlparse(request.url)
    scheme = request.scheme
    if app.config.get("SERVER_URL"):
        scheme = urlparse(app.config["SERVER_URL"]).scheme or request.scheme
    return {
        "https": "on" if scheme == "https" else "off",
        "http_host": request.host,
        "server_port": url_data.port,
        "script_name": request.path,
        "get_data": request.args.copy(),
        "post_data": request.form.copy(),
    }


USERDATA_MAPPING = {
    "displayname": "display_name",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "username",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": "first_name",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": "last_name",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "email",
    "http://schemas.xmlsoap.org/claims/Group": "desk",
    "http://schemas.microsoft.com/ws/2008/06/identity/claims/role": "role",
}


def get_userdata(saml_data):
    userdata = {}
    for src, dest in USERDATA_MAPPING.items():
        try:
            userdata[dest] = saml_data[src][0]
        except (KeyError, IndexError):
            continue
    return userdata


@bp.route("/login/saml", methods=["GET", "POST"])
def index():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    errors = []

    if "slo" in request.args:
        name_id = None
        session_index = None
        if SESSION_NAME_ID in session:
            name_id = session[SESSION_NAME_ID]
        if SESSION_SESSION_ID in session:
            session_index = session[SESSION_SESSION_ID]
        return redirect(auth.logout(name_id=name_id, session_index=session_index))
    elif "acs" in request.args or request.form:
        auth.process_response()
        errors = auth.get_errors()
        if len(errors) == 0:
            session[SESSION_NAME_ID] = auth.get_nameid()
            session[SESSION_SESSION_ID] = auth.get_session_index()
            session[SESSION_USERDATA_KEY] = auth.get_attributes()
        else:
            logger.error("SAML %s reason=%s", errors, auth.get_last_error_reason())
            return jsonify(
                {
                    "req": req,
                    "errors": errors,
                    "error_reason": auth.get_last_error_reason(),
                }
            )
    elif "sls" in request.args:

        def dscb():
            session.clear()

        url = auth.process_slo(delete_session_cb=dscb)
        errors = auth.get_errors()
        if len(errors) == 0:
            if url is not None:
                return redirect(url)

    if session.get(SESSION_NAME_ID):
        return auth_user(session[SESSION_NAME_ID], get_userdata(session[SESSION_USERDATA_KEY]))

    return redirect(auth.login())


@bp.route("/login/saml_metadata")
def metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers["Content-Type"] = "text/xml"
    else:
        resp = make_response(", ".join(errors), 500)
    return resp

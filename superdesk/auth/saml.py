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

from flask import current_app as app, request, redirect, make_response, session, jsonify
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from superdesk.auth import auth_user


bp = superdesk.Blueprint('saml', __name__)
logger = logging.getLogger(__name__)


def init_app(app):
    app.client_config['saml_auth'] = False
    if app.config.get('SAML_PATH'):
        app.client_config['saml_auth'] = True
        app.client_config['saml_label'] = app.config['SAML_LABEL']
        superdesk.blueprint(bp, app)


def init_saml_auth(req):
    auth = OneLogin_Saml2_Auth(req, custom_base_path=app.config['SAML_PATH'])
    return auth


def prepare_flask_request(request):
    url_data = urlparse(request.url)
    return {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.host,
        'server_port': url_data.port,
        'script_name': request.path,
        'get_data': request.args.copy(),
        'post_data': request.form.copy(),
    }


@bp.route('/login/saml', methods=['GET', 'POST'])
def index():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    errors = []

    if 'slo' in request.args:
        name_id = None
        session_index = None
        if 'samlNameId' in session:
            name_id = session['samlNameId']
        if 'samlSessionIndex' in session:
            session_index = session['samlSessionIndex']
        return redirect(auth.logout(name_id=name_id, session_index=session_index))
    elif 'acs' in request.args or request.form:
        auth.process_response()
        errors = auth.get_errors()
        if len(errors) == 0:
            session['samlUserdata'] = auth.get_attributes()
            session['samlNameId'] = auth.get_nameid()
            session['samlSessionIndex'] = auth.get_session_index()
        else:
            logger.error('SAML %s reason=%s', errors, auth.get_last_error_reason())
            return jsonify({
                'req': req,
                'errors': errors,
                'error_reason': auth.get_last_error_reason(),
            })
    elif 'sls' in request.args:
        def dscb():
            session.clear()
        url = auth.process_slo(delete_session_cb=dscb)
        errors = auth.get_errors()
        if len(errors) == 0:
            if url is not None:
                return redirect(url)

    if session.get('samlNameId'):
        return auth_user(session['samlNameId'])

    return redirect(auth.login())


@bp.route('/login/saml_metadata')
def metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
    else:
        resp = make_response(', '.join(errors), 500)
    return resp

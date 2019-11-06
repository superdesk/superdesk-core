import json
from base64 import b64encode
from requests.auth import _basic_auth_str
from flask import url_for


RESOURCES = (
    'archive', 'assignments', 'contacts',
    'desks', 'events', 'planning', 'users'
)


def test_not_authenticated(prodapi_app, prodapi_client):
    """
    Send a not authenticated request:
        - make a request without a token
        - ensure that request is not authenticated by prod api

    :param prodapi_app: prod api app
    :type prodapi_app: eve.flaskapp.Eve
    :param prodapi_client: client for prod api
    :type prodapi_client: flask.testing.FlaskClient
    """

    with prodapi_app.test_request_context():
        for resource in RESOURCES:
            # we send a request without a token
            resp = prodapi_client.get(
                url_for('{}|resource'.format(resource))
            )
            resp_data = json.loads(resp.data)
            # we get a 401 response
            assert resp.status_code == 401
            assert resp_data['_status'] == 'ERR'


def test_authenticated(prodapi_app, superdesk_app, prodapi_client, superdesk_client, auth_server_registered_client):
    """
    Send an authenticated request:
        - register client for auth server with all possible scopes
        - retrieve an acceess token from auth server by providing `id` and `password`
        - make a request with a token
        - ensure that request is authenticated by prod api

    :param prodapi_app: prod api app
    :type prodapi_app: eve.flaskapp.Eve
    :param prodapi_client: client for prod api
    :type prodapi_client: flask.testing.FlaskClient
    :param superdesk_app: superdesk api app
    :type superdesk_app: eve.flaskapp.Eve
    :param superdesk_client: client for superdesk api
    :type superdesk_client: flask.testing.FlaskClient
    """

    # we send client id and password to get an access token
    with superdesk_app.test_request_context():
        resp = superdesk_client.post(
            url_for('auth_server.issue_token'),
            data={
                'grant_type': 'client_credentials'
            },
            headers={
                "Authorization": _basic_auth_str('0102030405060708090a0b0c', 'secret_pwd_123')
            }
        )
        # we get an access token
        resp_data = json.loads(resp.data)
        assert resp.status_code == 200
        assert resp_data['token_type'] == 'Bearer'
        assert resp_data

import json
import pytest
from requests.auth import _basic_auth_str
from flask import url_for

from ..conftest import get_test_prodapi_app


RESOURCES = (
    'archive',
    'assignments',
    'contacts',
    'desks',
    'events',
    'planning',
    'users'
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


@pytest.mark.parametrize(
    'auth_server_registered_clients',
    [('ARCHIVE_READ',)],
    indirect=True
)
def test_authenticated(superdesk_app, superdesk_client, auth_server_registered_clients):
    """
    Send an authenticated request:
        - register client for auth server
        - retrieve an acceess token from auth server by providing `id` and `password`
        - make a request with a token
        - ensure that request is authenticated by prod api

    :param superdesk_app: superdesk api app
    :type superdesk_app: eve.flaskapp.Eve
    :param superdesk_client: client for superdesk api
    :type superdesk_client: flask.testing.FlaskClient
    """

    client_id = auth_server_registered_clients[0]['client_id']
    password = auth_server_registered_clients[0]['password']

    # we send a client id and password to get an access token
    with superdesk_app.test_request_context():
        resp = superdesk_client.post(
            url_for('auth_server.issue_token'),
            data={
                'grant_type': 'client_credentials'
            },
            headers={
                'Authorization': _basic_auth_str(client_id, password)
            }
        )

    # we get an access token
    resp_data = json.loads(resp.data)
    assert resp.status_code == 200
    assert resp_data['token_type'] == 'Bearer'
    assert 'access_token' in resp_data

    # we drop a superdesk flask app and client to avoid conflict between flask apps
    del superdesk_app
    del superdesk_client

    # we create a prodapi flask app and client
    prodapi_app = get_test_prodapi_app()
    prodapi_client = prodapi_app.test_client()

    # we send a request with an auth token
    token = resp_data['access_token']
    with prodapi_app.test_request_context():
        for resource in ('archive',):
            # we send a request without a token
            resp = prodapi_client.get(
                url_for('{}|resource'.format(resource)),
                headers={
                    'Authorization': 'Bearer {}'.format(token)
                }
            )

    # we get a 401 response
    assert resp.status_code == 200

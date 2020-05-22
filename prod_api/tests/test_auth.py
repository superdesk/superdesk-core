import json
import time
import pytest
from requests.auth import _basic_auth_str
from flask import url_for

from superdesk.auth_server.scopes import Scope

from ..conftest import get_test_prodapi_app, teardown_app


RESOURCES = (
    'archive',
    'assignments',
    'contacts',
    'desks',
    'events',
    'planning',
    'users'
)

SCOPES = tuple(i.name for i in Scope)


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
            resp_data = json.loads(resp.data.decode('utf-8'))
            # we get a 401 response
            assert resp.status_code == 401
            assert resp_data['_status'] == 'ERR'


@pytest.mark.parametrize('auth_server_registered_clients', [(('ARCHIVE_READ',),)], indirect=True)
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
    resp_data = json.loads(resp.data.decode('utf-8'))
    assert resp.status_code == 200
    assert resp_data['token_type'] == 'Bearer'
    assert 'access_token' in resp_data

    # we drop a superdesk flask app and client to avoid conflict between flask apps
    teardown_app(superdesk_app)
    del superdesk_client

    # we create a prodapi flask app and client
    prodapi_app = get_test_prodapi_app()
    prodapi_client = prodapi_app.test_client()

    # we send a request with an auth token
    token = resp_data['access_token']
    with prodapi_app.test_request_context():
        for resource in ('archive',):
            # we send a request with a token
            resp = prodapi_client.get(
                url_for('{}|resource'.format(resource)),
                headers={
                    'Authorization': 'Bearer {}'.format(token)
                }
            )

    # we get a 200 response
    assert resp.status_code == 200


@pytest.mark.parametrize('auth_server_registered_clients', [(('ARCHIVE_READ',),)], indirect=True)
def test_bad_shared_key(superdesk_app, superdesk_client, auth_server_registered_clients):
    """
    Send a request with a token which is signed and verified using different secrets:
        - register client for auth server
        - retrieve an acceess token from auth server by providing `id` and `password`
        - make a request with a token
        - ensure that request is NOT authenticated by prod api, because of different shared secret

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
    resp_data = json.loads(resp.data.decode('utf-8'))
    token = resp_data['access_token']

    # we drop a superdesk flask app and client to avoid conflict between flask apps
    teardown_app(superdesk_app)
    del superdesk_client

    # we create a prodapi flask app and client
    prodapi_app = get_test_prodapi_app()
    prodapi_client = prodapi_app.test_client()

    # we change `AUTH_SERVER_SHARED_SECRET`
    prodapi_app.config['AUTH_SERVER_SHARED_SECRET'] = '7fZOf0VI9T70vU5uNlKLrc5GlabxVgl6'

    # we send a request with an auth token
    with prodapi_app.test_request_context():
        for resource in ('archive',):
            # we send a request with a token
            resp = prodapi_client.get(
                url_for('{}|resource'.format(resource)),
                headers={
                    'Authorization': 'Bearer {}'.format(token)
                }
            )
            resp_data = json.loads(resp.data.decode('utf-8'))

    # we get a 401 response
    assert resp.status_code == 401
    assert resp_data == {
        '_status': 'ERR',
        '_error': {
            'code': 401,
            'message': 'Please provide proper credentials'
        }
    }


@pytest.mark.parametrize('issued_tokens', [(SCOPES, tuple())], indirect=True)
def test_scopes(issued_tokens, prodapi_app, prodapi_client):
    """
    Send a request with 'all scopes' token:
        - make a requests to all endpoints with a token
        - ensure that all requests are authorized by prod api

    Send a request with 'empty scopes' token:
        - make a requests to all endpoints with a token
        - ensure that all requests are NOT authorized by prod api due to empty scopes

    :param issued_tokens: list of tokens provided by `issued_tokens` fixture
    :type issued_tokens: list
    :param prodapi_app: prod api app
    :type prodapi_app: eve.flaskapp.Eve
    :param prodapi_client: client for prod api
    :type prodapi_client: flask.testing.FlaskClient
    """

    access_token_all_scopes = issued_tokens[0]['access_token']
    access_token_no_scopes = issued_tokens[1]['access_token']

    with prodapi_app.test_request_context():
        for resource in RESOURCES:
            # we send a requests with 'empty scopes' token
            resp = prodapi_client.get(
                url_for('{}|resource'.format(resource)),
                headers={
                    'Authorization': 'Bearer {}'.format(access_token_no_scopes)
                }
            )
            resp_data = json.loads(resp.data.decode('utf-8'))
            # we get a 403 response
            assert resp.status_code == 403
            assert resp_data == {
                '_status': 'ERR',
                '_error': {
                    'code': 403,
                    'message': 'Invalid scope'
                }
            }
            # we send a requests with 'all scopes' token
            resp = prodapi_client.get(
                url_for('{}|resource'.format(resource)),
                headers={
                    'Authorization': 'Bearer {}'.format(access_token_all_scopes)
                }
            )
            # we get a 200 response
            assert resp.status_code == 200


@pytest.mark.parametrize('issued_tokens', [(("DESKS_READ",),)], indirect=True)
def test_scopes_partial(issued_tokens, prodapi_app):
    """
    Send a request with DESKS_READ scope token to `desks` and `items`:
        - make requests to `desks` and `items` endpoints
        - ensure that only request to `desk` is authorized

    :param prodapi_app: prod api app
    :type prodapi_app: eve.flaskapp.Eve
    :param issued_tokens: list of tokens provided by `issued_tokens` fixture
    :type issued_tokens: list
    """

    access_token = issued_tokens[0]['access_token']
    prodapi_client = prodapi_app.test_client()

    with prodapi_app.test_request_context():
        # we send a request with 'DESKS_READ scope' token to desks endpoint
        resp = prodapi_client.get(
            url_for('desks|resource'),
            headers={
                'Authorization': 'Bearer {}'.format(access_token)
            }
        )
        # we get a 200 response
        assert resp.status_code == 200

        # we send a request with 'DESKS_READ scope' token to items endpoint
        resp = prodapi_client.get(
            url_for('archive|resource'),
            headers={
                'Authorization': 'Bearer {}'.format(access_token)
            }
        )
        resp_data = json.loads(resp.data.decode('utf-8'))
        # we get a 403 response
        assert resp.status_code == 403
        assert resp_data == {
            '_status': 'ERR',
            '_error': {
                'code': 403,
                'message': 'Invalid scope'
            }
        }


@pytest.mark.parametrize('auth_server_registered_clients', [(('ARCHIVE_READ',),)], indirect=True)
@pytest.mark.parametrize('superdesk_app', [{'AUTH_SERVER_EXPIRATION_DELAY': 1}, ], indirect=True)
def test_token_expired(superdesk_app, superdesk_client, auth_server_registered_clients):
    """
    Send a request with an expired token:
        - register client for auth server
        - retrieve an acceess token from auth server by providing `id` and `password`
        - wait until token expires
        - make a request with an expired token
        - ensure that request is NOT authenticated by prod api

    :param superdesk_app: superdesk api app
    :type superdesk_app: eve.flaskapp.Eve
    :param superdesk_client: client for superdesk api
    :type superdesk_client: flask.testing.FlaskClient
    """

    client_id = auth_server_registered_clients[0]['client_id']
    password = auth_server_registered_clients[0]['password']
    expiration_delay = superdesk_app.config['AUTH_SERVER_EXPIRATION_DELAY']

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
    assert resp.status_code == 200
    resp_data = json.loads(resp.data.decode('utf-8'))
    token = resp_data['access_token']

    # we drop a superdesk flask app and client to avoid conflict between flask apps
    teardown_app(superdesk_app)
    del superdesk_client

    # wait until token expire
    time.sleep(expiration_delay + 1)

    # we create a prodapi flask app and client
    prodapi_app = get_test_prodapi_app()
    prodapi_client = prodapi_app.test_client()

    # we send a request with an expired auth token
    with prodapi_app.test_request_context():
        for resource in ('archive',):
            # we send a request with a token
            resp = prodapi_client.get(
                url_for('{}|resource'.format(resource)),
                headers={
                    'Authorization': 'Bearer {}'.format(token)
                }
            )

    # we get a 401 response
    assert resp.status_code == 401

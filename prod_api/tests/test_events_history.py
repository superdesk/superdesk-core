import pytest
import json
from flask import url_for

from superdesk import get_resource_service


def test_service_get(prodapi_app_with_data):
    """
    Test fetching items using `events_history` service
    :param prodapi_app_with_data: prod api app with filled data
    """

    with prodapi_app_with_data.app_context():
        items_service = get_resource_service('events_history')

        assert len(list(items_service.get(req=None, lookup={}))) == 2


def test_readonly(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that `events_history` endpoint is readonly
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        for method, status in (('get', 200), ('post', 405), ('patch', 405), ('put', 405), ('delete', 405)):
            # we send a request
            resp = getattr(prodapi_app_with_data_client, method)(
                url_for('events_history|resource')
            )
            # we get a response
            assert resp.status_code == status


def test_excluded_fields(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that fields which are listed as `excluded_fields` are not in the response.
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        # list
        resp = prodapi_app_with_data_client.get(url_for('events_history|resource'))
        resp_data = json.loads(resp.data.decode('utf-8'))
        item = resp_data['_items'][0]

        with pytest.raises(KeyError):
            item['update']['_etag']

        with pytest.raises(KeyError):
            item['update']['_links']

        with pytest.raises(KeyError):
            item['update']['_status']

        with pytest.raises(KeyError):
            item['update']['_updated']

        with pytest.raises(KeyError):
            item['update']['_created']

        with pytest.raises(KeyError):
            item['update']['_id']

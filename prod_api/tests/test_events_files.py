import json
from flask import url_for

from superdesk import get_resource_service


def test_service_get(prodapi_app_with_data):
    """
    Test fetching items using `events_files` service
    :param prodapi_app_with_data: prod api app with filled data
    """

    with prodapi_app_with_data.app_context():
        items_service = get_resource_service("events_files")

        assert len(list(items_service.get(req=None, lookup={}))) == 2


def test_readonly(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that `events_files` endpoint is readonly
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        for method, status in (("get", 200), ("post", 405), ("patch", 405), ("put", 405), ("delete", 405)):
            # we send a request
            resp = getattr(prodapi_app_with_data_client, method)(url_for("events_files|resource"))
            # we get a response
            assert resp.status_code == status


def test_excluded_fields(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that fields which are listed as `excluded_fields` are not in the response.
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    excluded_fields = {
        "_etag",
        "_type",
        "_updated",
        "_created",
        "_current_version",
        "_links",
    }

    with prodapi_app_with_data.test_request_context():
        # list
        resp = prodapi_app_with_data_client.get(url_for("events_files|resource"))
        resp_data = json.loads(resp.data.decode("utf-8"))

        for item in resp_data["_items"]:
            assert len(set(item.keys()) & excluded_fields) == 0

        # details
        item = resp_data["_items"][0]
        resp = prodapi_app_with_data_client.get(
            url_for("events_files|item_lookup", _id=item["_id"]),
        )
        resp_data = json.loads(resp.data.decode("utf-8"))

        assert len(set(resp_data.keys()) & excluded_fields) == 0

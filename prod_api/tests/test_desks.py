import json
from flask import url_for

from superdesk import get_resource_service


def test_service_get(prodapi_app_with_data):
    """
    Test fetching items using `desks` service
    :param prodapi_app_with_data: prod api app with filled data
    """

    with prodapi_app_with_data.app_context():
        items_service = get_resource_service("desks")

        assert len(list(items_service.get(req=None, lookup={}))) == 2


def test_readonly(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that `desks` endpoint is readonly
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        for method, status in (("get", 200), ("post", 405), ("patch", 405), ("put", 405), ("delete", 405)):
            # we send a request
            resp = getattr(prodapi_app_with_data_client, method)(url_for("desks|resource"))
            # we get a response
            assert resp.status_code == status


def test_excluded_fields(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that fields which are listed as `excluded_fields` are not in the response.
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    excluded_fields = {
        "default_content_template",
        "working_stage",
        "incoming_stage",
        "desk_metadata",
        "content_expiry",
        "_etag",
        "_type",
        "_updated",
        "_created",
        "_current_version",
        "_links",
    }

    with prodapi_app_with_data.test_request_context():
        # list
        resp = prodapi_app_with_data_client.get(url_for("desks|resource"))
        resp_data = json.loads(resp.data.decode("utf-8"))

        for item in resp_data["_items"]:
            assert len(set(item.keys()) & excluded_fields) == 0

        # details
        item = resp_data["_items"][0]
        resp = prodapi_app_with_data_client.get(
            url_for("desks|item_lookup", _id=item["_id"]),
        )
        resp_data = json.loads(resp.data.decode("utf-8"))

        assert len(set(resp_data.keys()) & excluded_fields) == 0


def test_filters(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Test filtering.
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        params = {"where": json.dumps({"name": "PROD"})}
        resp = prodapi_app_with_data_client.get(url_for("desks|resource", **params))
        resp_data = json.loads(resp.data.decode("utf-8"))
        assert len(resp_data["_items"]) == 1
        assert resp_data["_items"][0]["_id"] == "5d76113ab3af37dea3a2eb9e"

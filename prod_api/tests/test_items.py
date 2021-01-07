import json
from flask import url_for

from superdesk import get_resource_service
from apps.archive.common import ARCHIVE


def test_service_get(prodapi_app_with_data):
    """
    Test fetching items using `archive` service
    :param prodapi_app_with_data: prod api app with filled data
    """

    with prodapi_app_with_data.app_context():
        items_service = get_resource_service(ARCHIVE)

        assert len(list(items_service.get(req=None, lookup={}))) == 7


def test_readonly(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that `archive` endpoint is readonly
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        for method, status in (("get", 200), ("post", 405), ("patch", 405), ("put", 405), ("delete", 405)):
            # we send a request
            resp = getattr(prodapi_app_with_data_client, method)(url_for("archive|resource"))
            # we get a response
            assert resp.status_code == status


def test_excluded_fields(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that fields which are listed as `excluded_fields` are not in the response.
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    excluded_fields = {
        "fields_meta",
        "unique_id",
        "family_id",
        "event_id",
        "lock_session",
        "lock_action",
        "lock_time",
        "lock_user",
        "_etag",
        "_type",
        "_updated",
        "_created",
        "_current_version",
        "_links",
    }

    with prodapi_app_with_data.test_request_context():
        # list
        resp = prodapi_app_with_data_client.get(url_for("archive|resource"))
        resp_data = json.loads(resp.data.decode("utf-8"))

        for item in resp_data["_items"]:
            assert len(set(item.keys()) & excluded_fields) == 0

        # details
        item = resp_data["_items"][0]
        resp = prodapi_app_with_data_client.get(
            url_for("archive|item_lookup", _id=item["guid"]),
        )
        resp_data = json.loads(resp.data.decode("utf-8"))

        assert len(set(resp_data.keys()) & excluded_fields) == 0


def test_renditions(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that rendition links are correct.
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        # details
        resp = prodapi_app_with_data_client.get(
            url_for(
                "archive|item_lookup",
                _id="urn:newsml:localhost:5000:2019-08-14T15:02:48.032188:d1be79f4-1d08-464a-90ac-90542dde4e90",
            ),
        )
        resp_data = json.loads(resp.data.decode("utf-8"))

        assert resp_data["associations"]["editor_0"]["renditions"] == {
            "baseImage": {
                "height": 933,
                "href": "http://localhost:5500/prodapi/v1/assets/5d553c343031e2855a2e5664.jpg",
                "mimetype": "image/jpeg",
                "poi": {"x": 700, "y": 466},
                "width": 1400,
            },
            "original": {
                "height": 1280,
                "href": "http://localhost:5500/prodapi/v1/assets/5d553c333031e2855a2e5662.jpg",
                "mimetype": "image/jpeg",
                "poi": {"x": 960, "y": 640},
                "width": 1920,
            },
            "thumbnail": {
                "height": 120,
                "href": "http://localhost:5500/prodapi/v1/assets/5d553c343031e2855a2e5666.jpg",
                "mimetype": "image/jpeg",
                "poi": {"x": 90, "y": 60},
                "width": 180,
            },
            "viewImage": {
                "height": 426,
                "href": "http://localhost:5500/prodapi/v1/assets/5d553c343031e2855a2e5668.jpg",
                "mimetype": "image/jpeg",
                "poi": {"x": 320, "y": 213},
                "width": 640,
            },
        }


def test_filters(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Test filtering.
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """

    with prodapi_app_with_data.test_request_context():
        # specify desk using source
        params = {
            "source": json.dumps(
                {"query": {"filtered": {"filter": {"terms": {"task.desk": ["7777777775ec40943b60e"]}}}}}
            )
        }
        resp = prodapi_app_with_data_client.get(url_for("archive|resource", **params))
        resp_data = json.loads(resp.data.decode("utf-8"))

        assert len(resp_data["_items"]) == 1
        assert resp_data["_items"][0]["guid"] == "tag:localhost:5000:2019:1dbebe89-e808-43f5-a27c-91545dac896f"

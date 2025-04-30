from flask import url_for
from eve.utils import parse_request
from superdesk import get_resource_service


def test_service_get(prodapi_app_with_data):
    """
    Test fetching items using `user_availability` service
    :param prodapi_app_with_data: prod api app with filled data
    """
    items_service = get_resource_service("user_availability")
    with prodapi_app_with_data.test_request_context("?month=2023-05"):
        req = parse_request("user_availability")
        items = list(items_service.get(req=req, lookup=None))

        assert len(items)
        assert items[0]["username"] == "admin"

        assert items[0]["availability"]["2023-05-15"]["status"] == "available"
        assert items[0]["availability"]["2023-05-15"]["published_articles"] == 5

        assert items[0]["availability"]["2023-05-16"]["status"] == "partial"
        assert items[0]["availability"]["2023-05-16"]["published_events"] == 2

        assert items[0]["availability"]["2023-05-18"]["status"] == ""
        assert items[0]["availability"]["2023-05-18"]["published_articles"] == 3


def test_readonly(prodapi_app_with_data, prodapi_app_with_data_client):
    """
    Ensure that `user_availability` endpoint is readonly
    :param prodapi_app_with_data: prod api app with filled data
    :param prodapi_app_with_data_client: client for prod api app with filled data
    """
    with prodapi_app_with_data.test_request_context():
        for method, status in (("get", 200), ("post", 405), ("patch", 405), ("put", 405), ("delete", 405)):
            # we send a request
            resp = getattr(prodapi_app_with_data_client, method)(url_for("user_availability|resource"))
            # we get a response
            assert resp.status_code == status

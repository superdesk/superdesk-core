from flask import url_for


def test_service_get(superdesk_app, prodapi_app_with_data):
    """
    Test fetching items using `user_availability` service
    :param prodapi_app_with_data: prod api app with filled data
    """
    with superdesk_app.app_context():
        user = superdesk_app.data.find_one("users", req=None, username="admin")
        assert user
        superdesk_app.data.insert(
            "default_user_availability",
            [
                {"_id": user["_id"], "enabled": True},
            ],
        )
    with prodapi_app_with_data.test_client() as client:
        resp = client.get("/prodapi/v1/user_availability?month=2023-05")
        assert resp.status_code == 200
        items = resp.json["_items"]

        assert len(items) == 1
        assert items[0]["_id"]
        assert items[0]["username"] == "admin"

        assert {
            "date": "2023-05-15",
            "status": "available",
            "published_articles": 5,
            "published_events": 0,
        } in items[
            0
        ]["availability"]

        assert {
            "date": "2023-05-16",
            "status": "partial",
            "published_articles": 0,
            "published_events": 2,
        } in items[
            0
        ]["availability"]

        assert {
            "date": "2023-05-18",
            "status": "",
            "published_articles": 3,
            "published_events": 0,
        } in items[
            0
        ]["availability"]

        resp = client.get("/prodapi/v1/user_availability/{}?month=2023-05".format(items[0]["_id"]))
        assert resp.status_code == 200
        for key in items[0].keys():
            if key == "_links":
                continue
            assert resp.json[key] == items[0][key]

        resp = client.get("/prodapi/v1/user_availability")
        assert resp.json["_items"]
        assert resp.json["_items"][0]["availability"] == []


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

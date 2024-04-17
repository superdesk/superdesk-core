from unittest.mock import MagicMock
from pathlib import Path
from copy import deepcopy

from urllib.parse import urlencode
from flask import json, url_for

from superdesk import __version__ as superdesk_version
from superdesk.tests import TestCase, setup_auth_user
from superdesk.http_proxy import HTTPProxy, register_http_proxy


class HttpProxyTestCase(TestCase):
    proxy = HTTPProxy("test_proxy", internal_url="test/proxy", external_url="http://localhost:5001/api")

    def setUp(self):
        self.headers = []
        register_http_proxy(self.app, self.proxy)
        self.proxy.session.request = MagicMock()
        self.proxy.session.request.return_value = MagicMock(ok=True, status_code=200)

    def setupAuthUser(self):
        original_headers = self.headers
        new_headers = deepcopy(original_headers)
        new_headers.append(("Content-Type", "application/json"))
        self.headers = new_headers
        setup_auth_user(self)
        self.headers = original_headers
        auth_header = next((header for header in new_headers if header[0] == "Authorization"), None)
        if auth_header is not None:
            self.headers.append(auth_header)

    def test_url_for(self):
        with self.app.app_context():
            self.assertEqual(url_for("test_proxy"), "/api/test/proxy")
            self.assertEqual(url_for("test_proxy", _external=True), "http://localhost/api/test/proxy")

    def test_authentication(self):
        self.proxy.auth = False
        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        self.proxy.auth = True
        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 401)

        self.setupAuthUser()
        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_proxies_request_to_external_service(self):
        self.setupAuthUser()

        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.proxy.session.request.assert_called_with(
            url="http://localhost:5001/api",
            method="GET",
            allow_redirects=True,
            stream=True,
            timeout=(5, 30),
            headers={"User-Agent": f"Superdesk-{superdesk_version}"},
            data=b"",
        )

        response = self.client.get("/api/test/proxy/articles/abcd123/associations", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.proxy.session.request.assert_called_with(
            url="http://localhost:5001/api/articles/abcd123/associations?",
            method="GET",
            allow_redirects=True,
            stream=True,
            timeout=(5, 30),
            headers={"User-Agent": f"Superdesk-{superdesk_version}"},
            data=b"",
        )

    def test_http_methods(self):
        self.setupAuthUser()
        second_proxy = HTTPProxy(
            "second_proxy",
            internal_url="test/proxy2",
            external_url="http://localhost:5012/api/v2",
            http_methods=["GET", "DELETE"],
        )
        second_proxy.session.request = MagicMock()
        second_proxy.session.request.return_value = MagicMock(ok=False, status_code=200)
        register_http_proxy(self.app, second_proxy)

        # Test already registered proxy, allowing all methods
        self.assertEqual(self.client.options("/api/test/proxy", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/api/test/proxy", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post("/api/test/proxy", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.patch("/api/test/proxy", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.put("/api/test/proxy", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.delete("/api/test/proxy", headers=self.headers).status_code, 200)

        # Raises MethodNotAllowed when method not configured for proxy
        self.assertEqual(self.client.options("/api/test/proxy2", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/api/test/proxy2", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post("/api/test/proxy2", headers=self.headers).status_code, 405)
        self.assertEqual(self.client.patch("/api/test/proxy2", headers=self.headers).status_code, 405)
        self.assertEqual(self.client.put("/api/test/proxy2", headers=self.headers).status_code, 405)
        self.assertEqual(self.client.delete("/api/test/proxy2", headers=self.headers).status_code, 200)

    def test_passes_headers_from_request(self):
        self.setupAuthUser()
        headers = deepcopy(self.headers)
        headers.append(("X-Acme-Clientdatafoo", "testing_headers_123"))
        response = self.client.get("/api/test/proxy", headers=headers)
        self.assertEqual(response.status_code, 200)
        kw_call_args = self.proxy.session.request.call_args[1]
        self.assertEqual(kw_call_args["headers"]["X-Acme-Clientdatafoo"], "testing_headers_123")

    def test_passes_on_errors_from_external_service(self):
        self.setupAuthUser()

        self.proxy.session.request.return_value = MagicMock(ok=False, status_code=404)
        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_supports_multiple_proxies(self):
        self.setupAuthUser()
        second_proxy = HTTPProxy(
            "second_proxy", internal_url="test/proxy2", external_url="http://localhost:5012/api/v2"
        )
        second_proxy.session.request = MagicMock()
        second_proxy.session.request.return_value = MagicMock(ok=False, status_code=201)
        register_http_proxy(self.app, second_proxy)

        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/test/proxy2", headers=self.headers)
        self.assertEqual(response.status_code, 201)

    def test_json_body(self):
        self.setupAuthUser()
        json_data = {
            "first_name": "foo",
            "last_name": "bar",
            "value": 23,
        }
        json_str = json.dumps(json_data).encode("utf-8")
        response = self.client.post("/api/test/proxy/new_item", headers=self.headers, json=json_data)
        self.assertEqual(response.status_code, 200)
        kw_call_args = self.proxy.session.request.call_args[1]
        self.assertEqual(
            kw_call_args["headers"],
            {
                "User-Agent": f"Superdesk-{superdesk_version}",
                "Content-Type": "application/json",
                "Content-Length": str(len(json_str)),
            },
        )
        self.assertEqual(kw_call_args["data"], json_str)

    def test_form_body(self):
        self.setupAuthUser()
        form_data = {
            "first_name": "foo",
            "last_name": "bar",
            "value": 23,
        }
        form_str = urlencode(form_data).encode("utf-8")
        response = self.client.post("/api/test/proxy/new_item", headers=self.headers, data=form_data)
        self.assertEqual(response.status_code, 200)
        kw_call_args = self.proxy.session.request.call_args[1]
        self.assertEqual(
            kw_call_args["headers"],
            {
                "User-Agent": f"Superdesk-{superdesk_version}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(form_str)),
            },
        )
        self.assertEqual(kw_call_args["data"], form_str)

        form_data["avatar"] = (Path(__file__).parent / "io" / "fixtures" / "picture_bug.jpg").open("rb")
        response = self.client.post("/api/test/proxy/new_item", headers=self.headers, data=form_data)
        self.assertEqual(response.status_code, 200)
        kw_call_args = self.proxy.session.request.call_args[1]
        self.assertTrue(kw_call_args["headers"]["Content-Type"].startswith("multipart/form-data"))

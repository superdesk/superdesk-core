from pathlib import Path
from copy import deepcopy

from urllib.parse import urlencode
import requests
import requests_mock

from superdesk.core import json
from superdesk.flask import url_for, Response as FlaskResponse
from superdesk import __version__ as superdesk_version
from superdesk.tests import TestCase, setup_auth_user
from superdesk.http_proxy import HTTPProxy, register_http_proxy


@requests_mock.Mocker()
class HttpProxyTestCase(TestCase):
    proxy = HTTPProxy("test_proxy", internal_url="test/proxy", external_url="http://localhost:5001/api")

    def setUp(self):
        self.headers = []
        register_http_proxy(self.app, self.proxy)
        self.proxy.session = requests.Session()

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

    def test_url_for(self, mock_request):
        with self.app.app_context():
            self.assertEqual(url_for("test_proxy"), "/api/test/proxy")
            self.assertEqual(url_for("test_proxy", _external=True), "http://localhost/api/test/proxy")

    def test_authentication(self, mock_request):
        mock_request.get("http://localhost:5001/api", status_code=200)
        self.proxy.auth = False

        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        self.proxy.auth = True
        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 401)

        self.setupAuthUser()
        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_proxies_request_to_external_service(self, mock_request):
        mock_request.get(requests_mock.ANY, status_code=200)
        self.setupAuthUser()

        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.last_request.method, "GET")
        self.assertEqual(mock_request.last_request.url, "http://localhost:5001/api")
        self.assertEqual(mock_request.last_request.stream, True)
        self.assertEqual(mock_request.last_request.timeout, (5, 30))
        self.assertEqual(mock_request.last_request.headers.get("User-Agent"), f"Superdesk-{superdesk_version}")

        response = self.client.get("/api/test/proxy/articles/abcd123/associations", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.last_request.method, "GET")
        self.assertEqual(mock_request.last_request.url, "http://localhost:5001/api/articles/abcd123/associations")

    def test_http_methods(self, mock_request):
        mock_request.request(requests_mock.ANY, requests_mock.ANY, status_code=200)
        second_proxy = HTTPProxy(
            "second_proxy",
            internal_url="test/proxy2",
            external_url="http://localhost:5012/api/v2",
            http_methods=["GET", "DELETE"],
        )
        register_http_proxy(self.app, second_proxy)
        self.setupAuthUser()

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

    def test_passes_headers_from_request(self, mock_request):
        mock_request.get("http://localhost:5001/api", status_code=200)
        self.setupAuthUser()
        headers = deepcopy(self.headers)
        headers.append(("X-ACME-ClientDataFoo", "testing_headers_123"))
        response = self.client.get("/api/test/proxy", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.last_request.headers.get("X-ACME-ClientDataFoo"), "testing_headers_123")

    def test_passes_on_errors_from_external_service(self, mock_request):
        mock_request.get("http://localhost:5001/api", status_code=404)
        self.setupAuthUser()

        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_supports_multiple_proxies(self, mock_request):
        mock_request.get("http://localhost:5001/api", status_code=200)
        mock_request.get("http://localhost:5025/api/v3", status_code=201)
        third_proxy = HTTPProxy("third_proxy", internal_url="test/proxy3", external_url="http://localhost:5025/api/v3")
        register_http_proxy(self.app, third_proxy)
        self.setupAuthUser()

        response = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/test/proxy3", headers=self.headers)
        self.assertEqual(response.status_code, 201)

    def test_json_body(self, mock_request):
        json_data = {
            "first_name": "foo",
            "last_name": "bar",
            "value": 23,
        }
        json_str = json.dumps(json_data)

        mock_request.post(
            requests_mock.ANY, status_code=200, json=json_data, headers={"Content-Type": "application/json"}
        )
        self.setupAuthUser()

        response = self.client.post("/api/test/proxy/new_item", headers=self.headers, json=json_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.last_request.headers.get("User-Agent"), f"Superdesk-{superdesk_version}")
        self.assertEqual(mock_request.last_request.headers.get("Content-Type"), "application/json")
        self.assertEqual(mock_request.last_request.headers.get("Content-Length"), str(len(json_str)))
        self.assertEqual(mock_request.last_request.text, json_str)
        self.assertEqual(response.get_json(), json_data)

    def test_form_body(self, mock_request):
        self.setupAuthUser()
        form_data = {
            "first_name": "foo",
            "last_name": "bar",
            "value": 23,
        }
        form_str = urlencode(form_data)
        mock_request.post(
            requests_mock.ANY,
            status_code=200,
            text=form_str,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = self.client.post("/api/test/proxy/new_item", headers=self.headers, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.last_request.headers.get("User-Agent"), f"Superdesk-{superdesk_version}")
        self.assertEqual(mock_request.last_request.headers.get("Content-Type"), "application/x-www-form-urlencoded")
        self.assertEqual(mock_request.last_request.headers.get("Content-Length"), str(len(form_str)))
        self.assertEqual(mock_request.last_request.text, form_str)
        self.assertEqual(response.data, form_str.encode("utf-8"))

        form_data["avatar"] = (Path(__file__).parent / "io" / "fixtures" / "picture_bug.jpg").open("rb")
        form_str = urlencode(form_data)
        mock_request.post(
            requests_mock.ANY, status_code=200, text=form_str, headers={"Content-Type": "multipart/form-data"}
        )
        response = self.client.post("/api/test/proxy/new_item", headers=self.headers, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_request.last_request.headers.get("Content-Type").startswith("multipart/form-data"))
        self.assertEqual(response.data, form_str.encode("utf-8"))

    def test_cors(self, mock_request):
        self.setupAuthUser()

        response: FlaskResponse = self.client.options("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:9000")
        self.assertEqual(response.headers.get("Access-Control-Allow-Headers"), "Content-Type,Authorization,If-Match")
        self.assertEqual(response.headers.get("Access-Control-Allow-Credentials"), "true")
        self.assertEqual(response.headers.get("Access-Control-Allow-Methods"), "OPTIONS,GET,POST,PATCH,PUT,DELETE")

        json_data = {
            "first_name": "foo",
            "last_name": "bar",
            "value": 23,
        }
        mock_request.get(
            "http://localhost:5001/api",
            json=json_data,
            headers={"Content-Type": "application/json"},
        )
        response: FlaskResponse = self.client.get("/api/test/proxy", headers=self.headers)
        self.assertEqual(response.headers.get("Content-Type"), "application/json")
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:9000")
        self.assertEqual(response.headers.get("Access-Control-Allow-Headers"), "Content-Type,Authorization,If-Match")
        self.assertEqual(response.headers.get("Access-Control-Allow-Credentials"), "true")
        self.assertEqual(response.headers.get("Access-Control-Allow-Methods"), "OPTIONS,GET,POST,PATCH,PUT,DELETE")
        self.assertEqual(response.get_json(), json_data)

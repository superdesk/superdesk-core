from pathlib import Path
from copy import deepcopy

from urllib.parse import urlencode
import requests
import requests_mock
from quart.datastructures import FileStorage

from superdesk.core import json
from superdesk.flask import url_for, Response as FlaskResponse
from superdesk import __version__ as superdesk_version
from superdesk.tests import TestCase, setup_auth_user, markers
from superdesk.http_proxy import HTTPProxy, register_http_proxy


class HttpProxyTestCase(TestCase):
    proxy = HTTPProxy("test_proxy", internal_url="test/proxy", external_url="http://localhost:5001/api")

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.headers = []
        register_http_proxy(self.app, self.proxy)
        self.proxy.session = requests.Session()
        self.proxy.auth = False

    async def setupAuthUser(self):
        original_headers = self.headers
        new_headers = deepcopy(original_headers)
        new_headers.append(("Content-Type", "application/json"))
        self.headers = new_headers
        await setup_auth_user(self)
        self.headers = original_headers
        auth_header = next((header for header in new_headers if header[0] == "Authorization"), None)
        if auth_header is not None:
            self.headers.append(auth_header)

    async def test_url_for(self):
        async with self.app.test_request_context("/api/test/proxy"):
            self.assertEqual(url_for("test_proxy"), "/api/test/proxy")
            self.assertEqual(url_for("test_proxy", _external=True), "http://localhost/api/test/proxy")

    @markers.requires_auth_headers_fix
    async def test_authentication(self):
        with requests_mock.Mocker() as mock_request:
            mock_request.get("http://localhost:5001/api", status_code=200)
            self.proxy.auth = False

            response = await self.client.get("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.status_code, 200)

            self.proxy.auth = True
            response = await self.client.get("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.status_code, 401)

            await self.setupAuthUser()
            response = await self.client.get("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.status_code, 200)

    async def test_proxies_request_to_external_service(self):
        with requests_mock.Mocker() as mock_request:
            mock_request.get(requests_mock.ANY, status_code=200)
            await self.setupAuthUser()

            response = await self.client.get("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_request.last_request.method, "GET")
            self.assertEqual(mock_request.last_request.url, "http://localhost:5001/api")
            self.assertEqual(mock_request.last_request.stream, True)
            self.assertEqual(mock_request.last_request.timeout, (5, 30))
            self.assertEqual(mock_request.last_request.headers.get("User-Agent"), f"Superdesk-{superdesk_version}")

            response = await self.client.get("/api/test/proxy/articles/abcd123/associations", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_request.last_request.method, "GET")
            self.assertEqual(mock_request.last_request.url, "http://localhost:5001/api/articles/abcd123/associations")

    async def test_http_methods(self):
        with requests_mock.Mocker() as mock_request:
            mock_request.request(requests_mock.ANY, requests_mock.ANY, status_code=200)
            second_proxy = HTTPProxy(
                "second_proxy",
                internal_url="test/proxy2",
                external_url="http://localhost:5012/api/v2",
                http_methods=["GET", "DELETE"],
                auth=False,
            )
            register_http_proxy(self.app, second_proxy)
            await self.setupAuthUser()

            # Test already registered proxy, allowing all methods
            self.assertEqual((await self.client.options("/api/test/proxy", headers=self.headers)).status_code, 200)
            self.assertEqual((await self.client.get("/api/test/proxy", headers=self.headers)).status_code, 200)
            self.assertEqual((await self.client.post("/api/test/proxy", headers=self.headers)).status_code, 200)
            self.assertEqual((await self.client.patch("/api/test/proxy", headers=self.headers)).status_code, 200)
            self.assertEqual((await self.client.put("/api/test/proxy", headers=self.headers)).status_code, 200)
            self.assertEqual((await self.client.delete("/api/test/proxy", headers=self.headers)).status_code, 200)

            # Raises MethodNotAllowed when method not configured for proxy
            self.assertEqual((await self.client.options("/api/test/proxy2", headers=self.headers)).status_code, 200)
            self.assertEqual((await self.client.get("/api/test/proxy2", headers=self.headers)).status_code, 200)
            self.assertEqual((await self.client.post("/api/test/proxy2", headers=self.headers)).status_code, 405)
            self.assertEqual((await self.client.patch("/api/test/proxy2", headers=self.headers)).status_code, 405)
            self.assertEqual((await self.client.put("/api/test/proxy2", headers=self.headers)).status_code, 405)
            self.assertEqual((await self.client.delete("/api/test/proxy2", headers=self.headers)).status_code, 200)

    async def test_passes_headers_from_request(self):
        with requests_mock.Mocker() as mock_request:
            mock_request.get("http://localhost:5001/api", status_code=200)
            await self.setupAuthUser()
            headers = deepcopy(self.headers)
            headers.append(("X-ACME-ClientDataFoo", "testing_headers_123"))
            response = await self.client.get("/api/test/proxy", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_request.last_request.headers.get("X-ACME-ClientDataFoo"), "testing_headers_123")

    async def test_passes_on_errors_from_external_service(self):
        with requests_mock.Mocker() as mock_request:
            mock_request.get("http://localhost:5001/api", status_code=404)
            await self.setupAuthUser()

            response = await self.client.get("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.status_code, 404)

    async def test_supports_multiple_proxies(self):
        with requests_mock.Mocker() as mock_request:
            mock_request.get("http://localhost:5001/api", status_code=200)
            mock_request.get("http://localhost:5025/api/v3", status_code=201)
            third_proxy = HTTPProxy(
                "third_proxy", internal_url="test/proxy3", external_url="http://localhost:5025/api/v3", auth=False
            )
            register_http_proxy(self.app, third_proxy)
            await self.setupAuthUser()

            response = await self.client.get("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.status_code, 200)

            response = await self.client.get("/api/test/proxy3", headers=self.headers)
            self.assertEqual(response.status_code, 201)

    async def test_json_body(self):
        with requests_mock.Mocker() as mock_request:
            json_data = {
                "first_name": "foo",
                "last_name": "bar",
                "value": 23,
            }
            json_str = json.dumps(json_data)

            mock_request.post(
                requests_mock.ANY, status_code=200, json=json_data, headers={"Content-Type": "application/json"}
            )
            await self.setupAuthUser()

            response = await self.client.post("/api/test/proxy/new_item", headers=self.headers, json=json_data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_request.last_request.headers.get("User-Agent"), f"Superdesk-{superdesk_version}")
            self.assertEqual(mock_request.last_request.headers.get("Content-Type"), "application/json")
            self.assertEqual(mock_request.last_request.headers.get("Content-Length"), str(len(json_str)))
            self.assertEqual(mock_request.last_request.text, json_str)
            self.assertEqual(await response.get_json(), json_data)

    async def test_form_body(self):
        with requests_mock.Mocker() as mock_request:
            await self.setupAuthUser()
            form_data = {
                "first_name": "foo",
                "last_name": "bar",
                "value": str(23),
            }
            form_str = urlencode(form_data)
            mock_request.post(
                requests_mock.ANY,
                status_code=200,
                text=form_str,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = await self.client.post("/api/test/proxy/new_item", headers=self.headers, form=form_data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_request.last_request.headers.get("User-Agent"), f"Superdesk-{superdesk_version}")
            self.assertEqual(mock_request.last_request.headers.get("Content-Type"), "application/x-www-form-urlencoded")
            self.assertEqual(mock_request.last_request.headers.get("Content-Length"), str(len(form_str)))
            self.assertEqual(mock_request.last_request.text, form_str)
            self.assertEqual(await response.get_data(), form_str.encode("utf-8"))

            files = dict(
                avatar=FileStorage(
                    (Path(__file__).parent / "io" / "fixtures" / "picture_bug.jpg").open("rb"),
                    filename="picture_bug.jpg",
                )
            )
            form_str = urlencode(form_data)
            mock_request.post(
                requests_mock.ANY, status_code=200, text=form_str, headers={"Content-Type": "multipart/form-data"}
            )
            response = await self.client.post(
                "/api/test/proxy/new_item", headers=self.headers, form=form_data, files=files
            )
            self.assertEqual(response.status_code, 200)
            print(mock_request.last_request.headers.get("Content-Type"))
            self.assertTrue(mock_request.last_request.headers.get("Content-Type").startswith("multipart/form-data"))
            self.assertEqual(await response.get_data(), form_str.encode("utf-8"))

    async def test_cors(self):
        with requests_mock.Mocker() as mock_request:
            await self.setupAuthUser()

            response: FlaskResponse = await self.client.options("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:9000")
            self.assertEqual(
                response.headers.get("Access-Control-Allow-Headers"), "Content-Type,Authorization,If-Match"
            )
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
            response: FlaskResponse = await self.client.get("/api/test/proxy", headers=self.headers)
            self.assertEqual(response.headers.get("Content-Type"), "application/json")
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:9000")
            self.assertEqual(
                response.headers.get("Access-Control-Allow-Headers"), "Content-Type,Authorization,If-Match"
            )
            self.assertEqual(response.headers.get("Access-Control-Allow-Credentials"), "true")
            self.assertEqual(response.headers.get("Access-Control-Allow-Methods"), "OPTIONS,GET,POST,PATCH,PUT,DELETE")
            self.assertEqual(await response.get_json(), json_data)

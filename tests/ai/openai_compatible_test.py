# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import asyncio
from unittest import mock

import aiohttp

from superdesk.ai.config import config as ai_config
from superdesk.ai.errors import AIErrorKind, AIProviderError
from superdesk.ai.providers.base import CompletionMessage, CompletionRequest
from superdesk.ai.providers.openai_compatible import OpenAICompatibleClient
from superdesk.tests import TestCase
from superdesk.tests.http_mocks import CallbackResult, mock_http

from .providers_test import ADMIN_USER, PROVIDER, USER_WITHOUT_PRIVILEGES, StubUserAuth

BASE_URL = "https://provider.test/v1"
API_KEY = "secret-key"
MODELS_URL = f"{BASE_URL}/models"
COMPLETIONS_URL = f"{BASE_URL}/chat/completions"

MODELS_PAYLOAD = {"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]}
COMPLETION_PAYLOAD = {
    "model": "gpt-4o-mini-2024-07-18",
    "choices": [{"message": {"role": "assistant", "content": "A headline"}}],
    "usage": {"prompt_tokens": 42, "completion_tokens": 7},
}


def capture_requests(http_mock, url: str, method: str, repeat: bool = False, **result_kwargs) -> list[dict]:
    """Mock a route and collect the keyword arguments each request was made with"""

    requests: list[dict] = []

    def callback(request_url, **kwargs):
        requests.append(kwargs)
        return CallbackResult(**result_kwargs)

    http_mock.add(url, method, callback=callback, repeat=repeat)
    return requests


def completion_request(**updates) -> CompletionRequest:
    return CompletionRequest(
        model="gpt-4o-mini",
        messages=[CompletionMessage(role="user", content="Write a headline")],
        **updates,
    )


class OpenAICompatibleClientTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.http_mock = mock_http(self)
        self.client = OpenAICompatibleClient(base_url=BASE_URL, api_key=API_KEY)

    async def test_complete_returns_the_content_model_and_token_usage(self):
        self.http_mock.post(COMPLETIONS_URL, payload=COMPLETION_PAYLOAD)

        result = await self.client.complete(completion_request())

        self.assertEqual(result.content, "A headline")
        self.assertEqual(result.model, "gpt-4o-mini-2024-07-18")
        self.assertEqual(result.prompt_tokens, 42)
        self.assertEqual(result.completion_tokens, 7)
        self.assertEqual(result.raw_usage, {"prompt_tokens": 42, "completion_tokens": 7})

    async def test_complete_sends_the_api_key_as_a_bearer_token(self):
        requests = self._capture_requests(COMPLETIONS_URL, "POST", payload=COMPLETION_PAYLOAD)

        await self.client.complete(completion_request())

        self.assertEqual(requests[0]["headers"]["Authorization"], f"Bearer {API_KEY}")

    async def test_complete_sends_the_configured_extra_headers(self):
        requests = self._capture_requests(COMPLETIONS_URL, "POST", payload=COMPLETION_PAYLOAD)
        client = OpenAICompatibleClient(
            base_url=BASE_URL,
            api_key=API_KEY,
            config={"headers": {"HTTP-Referer": "https://superdesk.org"}},
        )

        await client.complete(completion_request())

        self.assertEqual(requests[0]["headers"]["HTTP-Referer"], "https://superdesk.org")

    async def test_complete_asks_for_a_json_object_only_when_json_mode_is_on(self):
        requests = self._capture_requests(COMPLETIONS_URL, "POST", payload=COMPLETION_PAYLOAD, repeat=True)

        await self.client.complete(completion_request(json_mode=True, max_tokens=120, temperature=0.2))
        await self.client.complete(completion_request())

        self.assertEqual(requests[0]["json"]["response_format"], {"type": "json_object"})
        self.assertEqual(requests[0]["json"]["max_tokens"], 120)
        self.assertEqual(requests[0]["json"]["temperature"], 0.2)
        self.assertEqual(requests[0]["json"]["messages"], [{"role": "user", "content": "Write a headline"}])
        self.assertNotIn("response_format", requests[1]["json"])
        self.assertNotIn("max_tokens", requests[1]["json"])

    async def test_complete_raises_invalid_response_when_the_body_has_no_choices(self):
        self.http_mock.post(COMPLETIONS_URL, payload={"error": "no choices here"})

        with self.assertRaises(AIProviderError) as context:
            await self.client.complete(completion_request())

        self.assertEqual(context.exception.kind, AIErrorKind.INVALID_RESPONSE)

    async def test_complete_raises_invalid_response_when_the_body_is_not_json(self):
        self.http_mock.post(COMPLETIONS_URL, body="<html>gateway</html>")

        with self.assertRaises(AIProviderError) as context:
            await self.client.complete(completion_request())

        self.assertEqual(context.exception.kind, AIErrorKind.INVALID_RESPONSE)

    async def test_list_models_returns_the_model_ids(self):
        self.http_mock.get(MODELS_URL, payload=MODELS_PAYLOAD)

        self.assertEqual(await self.client.list_models(), ["gpt-4o-mini", "gpt-4o"])

    async def test_list_models_raises_invalid_response_when_the_body_has_no_data(self):
        self.http_mock.get(MODELS_URL, payload={"models": ["gpt-4o-mini"]})

        with self.assertRaises(AIProviderError) as context:
            await self.client.list_models()

        self.assertEqual(context.exception.kind, AIErrorKind.INVALID_RESPONSE)

    async def test_a_rejected_key_raises_an_auth_error(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.http_mock.get(MODELS_URL, status=status)

                with self.assertRaises(AIProviderError) as context:
                    await self.client.list_models()

                self.assertEqual(context.exception.kind, AIErrorKind.AUTH)
                self.assertEqual(context.exception.status_code, status)

    async def test_too_many_requests_raises_a_rate_limit_error(self):
        self.http_mock.get(MODELS_URL, status=429)

        with self.assertRaises(AIProviderError) as context:
            await self.client.list_models()

        self.assertEqual(context.exception.kind, AIErrorKind.RATE_LIMIT)

    async def test_a_server_error_raises_an_upstream_error(self):
        self.http_mock.get(MODELS_URL, status=503)

        with self.assertRaises(AIProviderError) as context:
            await self.client.list_models()

        self.assertEqual(context.exception.kind, AIErrorKind.UPSTREAM)

    async def test_a_rejected_request_raises_an_upstream_error(self):
        self.http_mock.get(MODELS_URL, status=400)

        with self.assertRaises(AIProviderError) as context:
            await self.client.list_models()

        self.assertEqual(context.exception.kind, AIErrorKind.UPSTREAM)

    async def test_a_provider_that_does_not_answer_raises_a_timeout_error(self):
        self.http_mock.get(MODELS_URL, exception=asyncio.TimeoutError())

        with self.assertRaises(AIProviderError) as context:
            await self.client.list_models()

        self.assertEqual(context.exception.kind, AIErrorKind.TIMEOUT)

    async def test_a_provider_that_cannot_be_reached_raises_an_upstream_error(self):
        self.http_mock.get(MODELS_URL, exception=aiohttp.ClientConnectionError("no route"))

        with self.assertRaises(AIProviderError) as context:
            await self.client.list_models()

        self.assertEqual(context.exception.kind, AIErrorKind.UPSTREAM)

    async def test_the_api_key_is_not_repeated_in_the_error_of_a_failed_request(self):
        self.http_mock.get(MODELS_URL, status=401, payload={"error": f"Incorrect API key provided: {API_KEY}"})

        with self.assertRaises(AIProviderError) as context:
            await self.client.list_models()

        self.assertNotIn(API_KEY, str(context.exception))
        self.assertNotIn(API_KEY, context.exception.message)

    async def test_no_authorization_header_is_sent_when_the_provider_has_no_api_key(self):
        for api_key in (None, ""):
            with self.subTest(api_key=api_key):
                requests = self._capture_requests(MODELS_URL, "GET", payload=MODELS_PAYLOAD)

                await OpenAICompatibleClient(base_url=BASE_URL, api_key=api_key).list_models()

                self.assertNotIn("Authorization", requests[0]["headers"])

    def _capture_requests(self, url: str, method: str, repeat: bool = False, **result_kwargs) -> list[dict]:
        return capture_requests(self.http_mock, url, method, repeat=repeat, **result_kwargs)


class AIRequestTimeoutConfigTestCase(TestCase):
    app_config = {"AI_REQUEST_TIMEOUT": 5}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.http_mock = mock_http(self)

    async def test_the_request_timeout_is_read_from_the_ai_request_timeout_setting(self):
        self.assertEqual(ai_config.request_timeout, 5)

    async def test_requests_use_the_configured_request_timeout(self):
        self.http_mock.get(MODELS_URL, payload=MODELS_PAYLOAD)

        with mock.patch("aiohttp.ClientSession", side_effect=aiohttp.ClientSession) as session_class:
            await OpenAICompatibleClient(base_url=BASE_URL, api_key=API_KEY).list_models()

        self.assertEqual(session_class.call_args.kwargs["timeout"].total, 5)


class AIProviderEndpointsTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._original_auth = self.async_app.auth
        self.async_app.auth = StubUserAuth(ADMIN_USER)
        self.addCleanup(self._restore_auth)
        self.http_mock = mock_http(self)

        response = await self.test_client.post(
            "/api/ai_providers",
            json={**PROVIDER, "base_url": BASE_URL, "api_key": API_KEY},
        )
        self.assertEqual(response.status_code, 201, await response.get_data())
        created = await response.get_json()
        self.provider_id = created["_id"]
        self.provider_etag = created["_etag"]

    def _restore_auth(self):
        self.async_app.auth = self._original_auth

    async def test_models_endpoint_stops_sending_a_key_once_it_has_been_cleared(self):
        requests = capture_requests(self.http_mock, MODELS_URL, "GET", payload=MODELS_PAYLOAD)

        response = await self.test_client.patch(
            f"/api/ai_providers/{self.provider_id}",
            json={"api_key": None},
            headers={"If-Match": self.provider_etag},
        )
        self.assertEqual(response.status_code, 200)

        response = await self.test_client.get(f"/api/ai_providers/{self.provider_id}/models")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Authorization", requests[0]["headers"])

    async def test_models_endpoint_returns_the_provider_models(self):
        self.http_mock.get(MODELS_URL, payload=MODELS_PAYLOAD)

        response = await self.test_client.get(f"/api/ai_providers/{self.provider_id}/models")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"models": ["gpt-4o-mini", "gpt-4o"]})

    async def test_models_endpoint_answers_404_for_an_unknown_provider(self):
        response = await self.test_client.get("/api/ai_providers/6543210987654321098765ab/models")

        self.assertEqual(response.status_code, 404)

    async def test_models_endpoint_requires_the_ai_studio_privilege(self):
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        response = await self.test_client.get(f"/api/ai_providers/{self.provider_id}/models")

        self.assertEqual(response.status_code, 403)

    async def test_models_endpoint_answers_502_when_the_provider_rejects_the_credentials(self):
        self.http_mock.get(MODELS_URL, status=401)

        response = await self.test_client.get(f"/api/ai_providers/{self.provider_id}/models")

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(API_KEY, (await response.get_json())["_message"])

    async def test_models_endpoint_answers_429_when_the_provider_rate_limits(self):
        self.http_mock.get(MODELS_URL, status=429)

        response = await self.test_client.get(f"/api/ai_providers/{self.provider_id}/models")

        self.assertEqual(response.status_code, 429)

    async def test_models_endpoint_answers_504_when_the_provider_does_not_answer(self):
        self.http_mock.get(MODELS_URL, exception=asyncio.TimeoutError())

        response = await self.test_client.get(f"/api/ai_providers/{self.provider_id}/models")

        self.assertEqual(response.status_code, 504)

    async def test_models_endpoint_answers_502_when_the_provider_fails(self):
        self.http_mock.get(MODELS_URL, status=500)

        response = await self.test_client.get(f"/api/ai_providers/{self.provider_id}/models")

        self.assertEqual(response.status_code, 502)

    async def test_test_endpoint_reports_a_provider_that_answers(self):
        self.http_mock.get(MODELS_URL, payload=MODELS_PAYLOAD)

        response = await self.test_client.post(f"/api/ai_providers/{self.provider_id}/test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"ok": True, "models_count": 2, "error": None})

    async def test_test_endpoint_reports_a_failing_provider_without_failing_the_request(self):
        self.http_mock.get(MODELS_URL, status=401)

        response = await self.test_client.post(f"/api/ai_providers/{self.provider_id}/test")

        self.assertEqual(response.status_code, 200)
        body = await response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["models_count"], 0)
        self.assertIn("401", body["error"])
        self.assertNotIn(API_KEY, body["error"])

    async def test_test_endpoint_requires_the_ai_studio_privilege(self):
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        response = await self.test_client.post(f"/api/ai_providers/{self.provider_id}/test")

        self.assertEqual(response.status_code, 403)

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json

from superdesk.ai.config import AIConfig
from superdesk.ai.config import config as ai_config
from superdesk.ai.errors import AIErrorKind, AIProviderError
from superdesk.ai.models import AIProvider
from superdesk.ai.providers import (
    allowed_provider_types,
    get_client,
    get_provider_type,
    register_provider_type,
)
from superdesk.ai.providers.base import AIProviderClient, CompletionRequest, CompletionResult
from superdesk.ai.providers.openai_compatible import OpenAICompatibleClient
from superdesk.ai.providers_service import AIProvidersService
from superdesk.core.auth.user_auth import UserAuthProtocol
from superdesk.core.types import Request
from superdesk.default_settings import AI_REQUEST_TIMEOUT
from superdesk.errors import AlreadyExistsError
from superdesk.tests import TestCase


class StubUserAuth(UserAuthProtocol):
    """Authenticates every request as a fixed user without a real session."""

    def __init__(self, user):
        self.user = user

    async def authenticate(self, request: Request):
        await self.continue_session(request, self.user)

    def get_current_user(self, request: Request):
        return self.user


ADMIN_USER = {"_id": "test-admin", "user_type": "administrator"}
USER_WITHOUT_PRIVILEGES = {"_id": "test-user", "user_type": "user", "privileges": {}}

PROVIDER = {
    "name": "OpenRouter",
    "provider_type": "openai_compatible",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "secret-key",
    "default_model": "openai/gpt-4o-mini",
}


class AIProvidersRestTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._original_auth = self.async_app.auth
        self.async_app.auth = StubUserAuth(ADMIN_USER)
        self.addCleanup(self._restore_auth)
        self.service = AIProvidersService()

    def _restore_auth(self):
        self.async_app.auth = self._original_auth

    async def _create_provider(self, **updates):
        response = await self.test_client.post("/api/ai_providers", json={**PROVIDER, **updates})
        self.assertEqual(response.status_code, 201, await response.get_data())
        return await response.get_json()

    async def _patch_provider(self, created, **updates):
        return await self.test_client.patch(
            f"/api/ai_providers/{created['_id']}",
            json=updates,
            headers={"If-Match": created["_etag"]},
        )

    async def test_post_response_does_not_contain_the_api_key(self):
        created = await self._create_provider()

        self.assertNotIn("api_key", created)
        self.assertEqual(created["name"], "OpenRouter")

    async def test_get_responses_do_not_contain_the_api_key(self):
        created = await self._create_provider()

        item = await (await self.test_client.get(f"/api/ai_providers/{created['_id']}")).get_json()
        self.assertNotIn("api_key", item)

        listing = await (await self.test_client.get("/api/ai_providers")).get_json()
        self.assertEqual(len(listing["_items"]), 1)
        self.assertNotIn("api_key", listing["_items"][0])

    async def test_patch_response_does_not_contain_the_api_key(self):
        created = await self._create_provider()

        response = await self.test_client.patch(
            f"/api/ai_providers/{created['_id']}",
            json={"api_key": "a-new-key"},
            headers={"If-Match": created["_etag"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("api_key", await response.get_json())

    async def test_patch_without_an_api_key_keeps_the_stored_one(self):
        created = await self._create_provider()

        response = await self.test_client.patch(
            f"/api/ai_providers/{created['_id']}",
            json={"name": "OpenRouter free"},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200)

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.name, "OpenRouter free")
        self.assertEqual(provider.api_key, "secret-key")

    async def test_patch_with_an_empty_api_key_keeps_the_stored_one(self):
        created = await self._create_provider()

        response = await self.test_client.patch(
            f"/api/ai_providers/{created['_id']}",
            json={"api_key": ""},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200)

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.api_key, "secret-key")

    async def test_patch_with_a_null_api_key_clears_the_stored_one(self):
        created = await self._create_provider()

        response = await self.test_client.patch(
            f"/api/ai_providers/{created['_id']}",
            json={"api_key": None},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200)

        provider = await self.service.find_by_id(created["_id"])
        self.assertIsNone(provider.api_key)

    async def test_patch_with_an_api_key_replaces_the_stored_one(self):
        created = await self._create_provider()

        response = await self.test_client.patch(
            f"/api/ai_providers/{created['_id']}",
            json={"api_key": "a-new-key"},
            headers={"If-Match": created["_etag"]},
        )
        self.assertEqual(response.status_code, 200)

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.api_key, "a-new-key")

    async def test_filtering_providers_by_api_key_is_rejected(self):
        await self._create_provider()

        response = await self.test_client.get(
            "/api/ai_providers?where=" + json.dumps({"api_key": {"$regex": "^s"}}),
        )

        self.assertEqual(response.status_code, 400)

    async def test_unknown_provider_type_is_rejected(self):
        response = await self.test_client.post("/api/ai_providers", json={**PROVIDER, "provider_type": "anthropic"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("provider_type", (await response.get_json())["_issues"])

    async def test_base_url_that_is_not_an_http_url_is_rejected(self):
        response = await self.test_client.post("/api/ai_providers", json={**PROVIDER, "base_url": "not-a-url"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("base_url", (await response.get_json())["_issues"])

    async def test_empty_name_is_rejected(self):
        response = await self.test_client.post("/api/ai_providers", json={**PROVIDER, "name": ""})

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", (await response.get_json())["_issues"])

    async def test_base_url_is_stored_without_a_trailing_slash(self):
        created = await self._create_provider(base_url="https://openrouter.ai/api/v1/")

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.base_url, "https://openrouter.ai/api/v1")

    async def test_provider_defaults_are_applied_on_create(self):
        created = await self._create_provider()

        provider = await self.service.find_by_id(created["_id"])
        self.assertTrue(provider.active)
        self.assertFalse(provider.is_default)
        self.assertEqual(provider.config, {})
        self.assertEqual(provider.available_models, [])

    async def test_creating_a_provider_whose_default_model_is_not_available_is_rejected(self):
        response = await self.test_client.post(
            "/api/ai_providers",
            json={**PROVIDER, "available_models": ["openai/gpt-4o"]},
        )

        self.assertEqual(response.status_code, 400)
        message = (await response.get_json())["_message"]
        self.assertIn("default_model", message)
        self.assertIn("available_models", message)

    async def test_creating_a_provider_whose_default_model_is_available_is_accepted(self):
        created = await self._create_provider(available_models=["openai/gpt-4o", "openai/gpt-4o-mini"])

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o", "openai/gpt-4o-mini"])
        self.assertEqual(provider.default_model, "openai/gpt-4o-mini")

    async def test_an_empty_available_models_allows_any_default_model(self):
        created = await self._create_provider(available_models=[], default_model="a-model-nobody-listed")

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.default_model, "a-model-nobody-listed")

    async def test_available_models_without_a_default_model_is_accepted(self):
        created = await self._create_provider(available_models=["openai/gpt-4o"], default_model=None)

        provider = await self.service.find_by_id(created["_id"])
        self.assertIsNone(provider.default_model)

    async def test_patch_setting_a_default_model_outside_available_models_is_rejected(self):
        created = await self._create_provider(available_models=["openai/gpt-4o-mini"])

        response = await self._patch_provider(created, default_model="openai/gpt-4o")

        self.assertEqual(response.status_code, 400)
        message = (await response.get_json())["_message"]
        self.assertIn("default_model", message)
        self.assertIn("available_models", message)

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.default_model, "openai/gpt-4o-mini")

    async def test_patch_dropping_the_default_model_from_available_models_is_rejected(self):
        created = await self._create_provider(available_models=["openai/gpt-4o", "openai/gpt-4o-mini"])

        response = await self._patch_provider(created, available_models=["openai/gpt-4o"])

        self.assertEqual(response.status_code, 400)
        message = (await response.get_json())["_message"]
        self.assertIn("default_model", message)
        self.assertIn("available_models", message)

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o", "openai/gpt-4o-mini"])

    async def test_patch_moving_the_default_model_and_the_list_together_is_accepted(self):
        created = await self._create_provider(available_models=["openai/gpt-4o-mini"])

        response = await self._patch_provider(
            created, available_models=["openai/gpt-4o"], default_model="openai/gpt-4o"
        )

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o"])
        self.assertEqual(provider.default_model, "openai/gpt-4o")

    async def test_patch_emptying_available_models_lifts_the_restriction(self):
        created = await self._create_provider(available_models=["openai/gpt-4o-mini"])

        response = await self._patch_provider(created, available_models=[], default_model="a-model-nobody-listed")

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, [])
        self.assertEqual(provider.default_model, "a-model-nobody-listed")

    async def test_patch_clearing_the_default_model_with_a_null_accepts_any_shortlist(self):
        """An explicit ``null`` clears the default model, so no shortlist can be in conflict with it"""

        created = await self._create_provider(available_models=["openai/gpt-4o-mini"])

        response = await self._patch_provider(created, available_models=["openai/gpt-4o"], default_model=None)

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertIsNone(provider.default_model)
        self.assertEqual(provider.available_models, ["openai/gpt-4o"])

    async def test_patch_of_a_malformed_available_models_is_a_field_error(self):
        """The cross-field check runs before the payload is validated, so it has to survive any shape"""

        created = await self._create_provider(available_models=["openai/gpt-4o-mini"])

        for available_models in ([123], ["openai/gpt-4o", None], "openai/gpt-4o", None, 5):
            with self.subTest(available_models=available_models):
                response = await self._patch_provider(created, available_models=available_models)

                self.assertEqual(response.status_code, 400, await response.get_data())
                provider = await self.service.find_by_id(created["_id"])
                self.assertEqual(provider.available_models, ["openai/gpt-4o-mini"])

    async def test_patch_of_an_unrelated_field_keeps_available_models(self):
        created = await self._create_provider(available_models=["openai/gpt-4o-mini"])

        response = await self._patch_provider(created, name="OpenRouter free")

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o-mini"])

    async def test_user_without_the_ai_studio_privilege_cannot_read_providers(self):
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        response = await self.test_client.get("/api/ai_providers")

        self.assertEqual(response.status_code, 403)

    async def test_user_without_the_ai_studio_privilege_cannot_head_providers(self):
        """A HEAD request is answered by the GET handler, so it has to be refused with it"""

        created = await self._create_provider()
        self.async_app.auth = StubUserAuth(USER_WITHOUT_PRIVILEGES)

        listing = await self.test_client.head("/api/ai_providers")
        item = await self.test_client.head(f"/api/ai_providers/{created['_id']}")

        self.assertEqual(listing.status_code, 403)
        self.assertEqual(item.status_code, 403)


class FakeProviderClient(AIProviderClient):
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(content="", model=request.model)

    async def list_models(self) -> list[str]:
        return []


class AIProviderRegistryTestCase(TestCase):
    async def test_openai_compatible_type_is_registered(self):
        self.assertIn("openai_compatible", allowed_provider_types)

        provider_type = get_provider_type("openai_compatible")
        self.assertIsNotNone(provider_type)
        self.assertEqual(provider_type.client_class, OpenAICompatibleClient)
        self.assertEqual(str(provider_type.label), "OpenAI compatible")

    async def test_get_provider_type_returns_none_for_an_unregistered_name(self):
        self.assertIsNone(get_provider_type("anthropic"))

    async def test_registering_a_type_twice_is_rejected(self):
        with self.assertRaises(AlreadyExistsError):
            register_provider_type("openai_compatible", FakeProviderClient)

    async def test_get_client_builds_the_registered_client_from_the_provider(self):
        provider = AIProvider.from_dict(
            {
                **PROVIDER,
                "config": {"headers": {"HTTP-Referer": "https://superdesk.org"}},
            }
        )

        client = get_client(provider)

        self.assertIsInstance(client, OpenAICompatibleClient)
        self.assertEqual(client.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(client.api_key, "secret-key")
        self.assertEqual(client.config, {"headers": {"HTTP-Referer": "https://superdesk.org"}})


class AIConfigTestCase(TestCase):
    async def test_the_module_config_default_matches_the_ai_request_timeout_setting(self):
        self.assertEqual(AIConfig.model_fields["request_timeout"].default, AI_REQUEST_TIMEOUT)
        self.assertEqual(ai_config.request_timeout, AI_REQUEST_TIMEOUT)


class AIProviderClientTestCase(TestCase):
    async def test_test_connection_reports_the_failure_instead_of_raising(self):
        class FailingClient(FakeProviderClient):
            async def list_models(self) -> list[str]:
                raise AIProviderError(AIErrorKind.AUTH, "Rejected credentials", 401)

        result = await FailingClient(base_url="https://example.com").test_connection()

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Rejected credentials")
        self.assertEqual(result.models_count, 0)

    async def test_test_connection_reports_the_number_of_models(self):
        class ListingClient(FakeProviderClient):
            async def list_models(self) -> list[str]:
                return ["one", "two"]

        result = await ListingClient(base_url="https://example.com").test_connection()

        self.assertTrue(result.ok)
        self.assertEqual(result.models_count, 2)
        self.assertIsNone(result.error)

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
import os
from unittest.mock import patch

from superdesk.ai.config import AIConfig, check_request_timeout
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
from superdesk.default_settings import AI_RATE_LIMIT_PER_MINUTE, AI_REQUEST_TIMEOUT
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


# User IDs are ObjectIds, as stored ones are: checking the desks of a user needs a real one
ADMIN_USER = {"_id": "6a0000000000000000000001", "user_type": "administrator"}
USER_WITHOUT_PRIVILEGES = {"_id": "6a0000000000000000000002", "user_type": "user", "privileges": {}}

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

    async def test_a_default_model_outside_available_models_is_accepted(self):
        """The shortlist restricts the actions, not the fallback the provider hands them"""

        created = await self._create_provider(available_models=["openai/gpt-4o"], default_model="a-model-nobody-listed")

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o"])
        self.assertEqual(provider.default_model, "a-model-nobody-listed")

    async def test_patch_setting_a_default_model_outside_available_models_is_accepted(self):
        created = await self._create_provider(available_models=["openai/gpt-4o-mini"])

        response = await self._patch_provider(created, default_model="a-model-nobody-listed")

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.default_model, "a-model-nobody-listed")

    async def test_available_models_without_a_default_model_is_accepted(self):
        created = await self._create_provider(available_models=["openai/gpt-4o"], default_model=None)

        provider = await self.service.find_by_id(created["_id"])
        self.assertIsNone(provider.default_model)

    async def test_an_empty_default_model_is_stored_as_none(self):
        """A form clearing the field can only send an empty string, so it means no default model"""

        created = await self._create_provider(default_model="")
        self.assertIsNone((await self.service.find_by_id(created["_id"])).default_model)

        created = await self._create_provider(default_model="openai/gpt-4o")
        response = await self._patch_provider(created, default_model="")

        self.assertEqual(response.status_code, 200, await response.get_data())
        self.assertIsNone((await self.service.find_by_id(created["_id"])).default_model)

    async def test_patch_of_a_malformed_available_models_is_a_field_error(self):
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

    async def _create_action(self, created, model):
        response = await self.test_client.post(
            "/api/ai_actions",
            json={
                "name": f"Suggest with {model}",
                "action_type": "suggestion",
                "input_fields": ["body_html"],
                "output_field": "headline",
                "provider": created["_id"],
                "model": model,
            },
        )
        self.assertEqual(response.status_code, 201, await response.get_data())
        return await response.get_json()

    async def test_patch_dropping_a_model_an_action_uses_is_rejected(self):
        created = await self._create_provider(available_models=["openai/gpt-4o", "openai/gpt-4o-mini"])
        await self._create_action(created, "openai/gpt-4o")

        response = await self._patch_provider(created, available_models=["openai/gpt-4o-mini"])

        self.assertEqual(response.status_code, 400)
        message = (await response.get_json())["_message"]
        self.assertIn("openai/gpt-4o", message)
        self.assertIn("Suggest with openai/gpt-4o", message)

        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o", "openai/gpt-4o-mini"])

    async def test_patch_dropping_a_model_no_action_uses_is_accepted(self):
        created = await self._create_provider(available_models=["openai/gpt-4o", "openai/gpt-4o-mini"])
        await self._create_action(created, "openai/gpt-4o-mini")

        response = await self._patch_provider(created, available_models=["openai/gpt-4o-mini"])

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o-mini"])

    async def test_patch_emptying_available_models_is_accepted_whatever_the_actions_use(self):
        """An empty shortlist allows every model, so no action can be left outside it"""

        created = await self._create_provider(available_models=["openai/gpt-4o"])
        await self._create_action(created, "openai/gpt-4o")

        response = await self._patch_provider(created, available_models=[])

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, [])

    async def test_patch_widening_available_models_is_accepted(self):
        created = await self._create_provider(available_models=["openai/gpt-4o"])
        await self._create_action(created, "openai/gpt-4o")

        response = await self._patch_provider(created, available_models=["openai/gpt-4o", "openai/gpt-4o-mini"])

        self.assertEqual(response.status_code, 200, await response.get_data())
        provider = await self.service.find_by_id(created["_id"])
        self.assertEqual(provider.available_models, ["openai/gpt-4o", "openai/gpt-4o-mini"])

    async def test_an_action_without_a_model_never_blocks_the_shortlist(self):
        """It runs on ``default_model``, which the shortlist does not restrict"""

        created = await self._create_provider(available_models=["openai/gpt-4o"])
        await self._create_action(created, None)

        response = await self._patch_provider(created, available_models=["openai/gpt-4o-mini"])

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

    async def test_the_module_config_default_matches_the_ai_rate_limit_setting(self):
        self.assertEqual(AIConfig.model_fields["rate_limit_per_minute"].default, AI_RATE_LIMIT_PER_MINUTE)

    def _check_request_timeout(self, request_timeout, web_timeout=None):
        environ = {"WEB_TIMEOUT": web_timeout} if web_timeout is not None else {}
        with (
            patch.dict(os.environ, environ),
            patch.object(ai_config, "request_timeout", request_timeout),
        ):
            if web_timeout is None:
                os.environ.pop("WEB_TIMEOUT", None)
            check_request_timeout()

    async def test_the_default_request_timeout_is_below_the_server_timeout(self):
        with self.assertNoLogs("superdesk.ai.config", "WARNING"):
            self._check_request_timeout(AI_REQUEST_TIMEOUT)

    async def test_a_request_timeout_the_server_gives_up_before_is_warned_about(self):
        for request_timeout, web_timeout in ((30, None), (40, "40"), (45, "not a number")):
            with self.subTest(request_timeout=request_timeout, web_timeout=web_timeout):
                with self.assertLogs("superdesk.ai.config", "WARNING") as logs:
                    self._check_request_timeout(request_timeout, web_timeout)

                self.assertIn("AI_REQUEST_TIMEOUT", logs.output[0])

    async def test_a_request_timeout_under_a_raised_server_timeout_is_accepted(self):
        with self.assertNoLogs("superdesk.ai.config", "WARNING"):
            self._check_request_timeout(45, "90")

    async def test_a_request_timeout_the_proxy_gives_up_before_is_warned_about(self):
        with self.assertLogs("superdesk.ai.config", "WARNING"):
            self._check_request_timeout(60, "90")


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

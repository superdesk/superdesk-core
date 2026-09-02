Feature: AI providers

    @auth
    Scenario: A provider is created and read back without its api key
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "api_key": "secret-key",
            "default_model": "openai/gpt-4o-mini"
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "default_model": "openai/gpt-4o-mini",
            "available_models": [],
            "active": true,
            "is_default": false
        }
        """
        And we get "api_key" does not exist
        When we get "/ai_providers/#ai_providers._id#"
        Then we get OK response
        And we get "api_key" does not exist
        When we get "/ai_providers"
        Then we get list with 1 items
        And we get "api_key" does not exist
        When we patch "/ai_providers/#ai_providers._id#"
        """
        {"label": "Free models"}
        """
        Then we get OK response
        And we get "api_key" does not exist

    @auth
    Scenario: Create fails with an unknown provider type
        When we post to "/ai_providers"
        """
        {"name": "Somewhere", "provider_type": "carrier_pigeon", "base_url": "https://provider.test/v1"}
        """
        Then we get error 400

    @auth
    Scenario: An empty api key on patch keeps the stored one
        Given a mocked AI provider at "https://provider.test/v1"
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "api_key": "secret-key"
        }
        """
        Then we get OK response
        When we patch "/ai_providers/#ai_providers._id#"
        """
        {"api_key": "", "label": "Free models"}
        """
        Then we get OK response
        When we get "/ai_providers/#ai_providers._id#/models"
        Then we get OK response
        And the AI provider was called with the api key "secret-key"

    @auth
    Scenario: A null api key on patch clears the stored one
        Given a mocked AI provider at "https://provider.test/v1"
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "api_key": "secret-key"
        }
        """
        Then we get OK response
        When we patch "/ai_providers/#ai_providers._id#"
        """
        {"api_key": null}
        """
        Then we get OK response
        When we get "/ai_providers/#ai_providers._id#/models"
        Then we get OK response
        And the AI provider was called with no api key

    @auth
    Scenario: Create fails with a default model outside available_models
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "available_models": ["openai/gpt-4o-mini"],
            "default_model": "openai/gpt-4o"
        }
        """
        Then we get error 400

    @auth
    Scenario: Patch fails when available_models drops the default model
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "available_models": ["openai/gpt-4o-mini", "openai/gpt-4o"],
            "default_model": "openai/gpt-4o"
        }
        """
        Then we get OK response
        When we patch "/ai_providers/#ai_providers._id#"
        """
        {"available_models": ["openai/gpt-4o-mini"]}
        """
        Then we get error 400
        When we patch "/ai_providers/#ai_providers._id#"
        """
        {"available_models": ["openai/gpt-4o-mini"], "default_model": "openai/gpt-4o-mini"}
        """
        Then we get OK response
        And we get existing resource
        """
        {"available_models": ["openai/gpt-4o-mini"], "default_model": "openai/gpt-4o-mini"}
        """

    @auth
    Scenario: The models endpoint lists the whole catalogue of the provider
        Given a mocked AI provider at "https://provider.test/v1"
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "api_key": "secret-key",
            "available_models": ["openai/gpt-4o-mini"],
            "default_model": "openai/gpt-4o-mini"
        }
        """
        Then we get OK response
        When we get "/ai_providers/#ai_providers._id#/models"
        Then we get OK response
        """
        {"models": ["openai/gpt-4o-mini", "openai/gpt-4o"]}
        """
        And the AI provider was called with the api key "secret-key"

    @auth
    Scenario: The test endpoint reports a provider that answers
        Given a mocked AI provider at "https://provider.test/v1"
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "api_key": "secret-key"
        }
        """
        Then we get OK response
        When we test the AI provider at "/ai_providers/#ai_providers._id#/test"
        Then we get OK response
        """
        {"ok": true, "models_count": 2}
        """

    @auth
    Scenario: The test endpoint reports a provider that fails as an answer, not as an error
        Given a mocked AI provider at "https://provider.test/v1"
        """
        {"status": 500}
        """
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "api_key": "secret-key"
        }
        """
        Then we get OK response
        When we test the AI provider at "/ai_providers/#ai_providers._id#/test"
        Then we get OK response
        """
        {"ok": false, "models_count": 0, "error": "__any_value__"}
        """

    @auth
    Scenario: Managing providers needs the ai_studio privilege
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "api_key": "secret-key"
        }
        """
        Then we get OK response
        When we login as user "ai_editor" with password "editor123" and user type "user"
        """
        {"privileges": {"ai": 1}}
        """
        And we get "/ai_providers"
        Then we get error 403
        When we get "/ai_providers/#ai_providers._id#"
        Then we get error 403
        When we get "/ai_providers/#ai_providers._id#/models"
        Then we get error 403
        When we post to "/ai_providers"
        """
        {"name": "Another one", "provider_type": "openai_compatible", "base_url": "https://provider.test/v1"}
        """
        Then we get error 403

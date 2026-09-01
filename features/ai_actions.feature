Feature: AI actions

    @auth
    Scenario: An action is created against a provider
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
        When we post to "/ai_actions"
        """
        {
            "name": "Headline suggestions",
            "action_type": "suggestion",
            "input_fields": ["body_html"],
            "output_field": "headline",
            "parameters": {"max_characters": 60},
            "provider": "#ai_providers._id#"
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "name": "Headline suggestions",
            "action_type": "suggestion",
            "input_fields": ["body_html"],
            "output_field": "headline",
            "parameters": {"max_characters": 60, "suggestions_count": 3, "temperature": 0.7},
            "content_profiles": [],
            "active": true
        }
        """
        When we get "/ai_actions"
        Then we get list with 1 items

    @auth
    Scenario: Create fails with an unknown action type
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "default_model": "openai/gpt-4o-mini"
        }
        """
        Then we get OK response
        When we post to "/ai_actions"
        """
        {
            "name": "Headline suggestions",
            "action_type": "haiku",
            "input_fields": ["body_html"],
            "output_field": "headline",
            "provider": "#ai_providers._id#"
        }
        """
        Then we get error 400

    @auth
    Scenario: Running an action answers with the suggestions of the provider and the event it wrote
        Given a mocked AI provider at "https://provider.test/v1"
        And an archive item "article-1" with data
        """
        {"profile": "story", "language": "en", "body_html": "<p>The council met on Tuesday.</p><p>It voted on the budget.</p>"}
        """
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
        When we post to "/ai_actions"
        """
        {
            "name": "Headline suggestions",
            "action_type": "suggestion",
            "input_fields": ["body_html"],
            "output_field": "headline",
            "parameters": {"max_characters": 60},
            "provider": "#ai_providers._id#"
        }
        """
        Then we get OK response
        When we run the AI action at "/ai_actions/#ai_actions._id#/run"
        """
        {"item_id": "article-1", "source": "authoring"}
        """
        Then we get OK response
        """
        {
            "suggestions": [
                {"text": "Council votes on budget", "over_limit": false},
                {"text": "Council backs the budget", "over_limit": false},
                {"text": "Budget passes at the council", "over_limit": false}
            ],
            "event_id": "__any_value__",
            "provider": "#ai_providers._id#",
            "model": "openai/gpt-4o-mini",
            "usage": {"input_tokens": 42, "output_tokens": 7}
        }
        """
        And the AI provider was called with the api key "secret-key"

    @auth
    Scenario: Running an action against an unknown item is a 404
        Given a mocked AI provider at "https://provider.test/v1"
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "default_model": "openai/gpt-4o-mini"
        }
        """
        Then we get OK response
        When we post to "/ai_actions"
        """
        {
            "name": "Headline suggestions",
            "action_type": "suggestion",
            "input_fields": ["body_html"],
            "output_field": "headline",
            "provider": "#ai_providers._id#"
        }
        """
        Then we get OK response
        When we run the AI action at "/ai_actions/#ai_actions._id#/run"
        """
        {"item_id": "no-such-article"}
        """
        Then we get error 404

    @auth
    Scenario: Running an action needs the ai privilege, configuring them is not enough
        Given a mocked AI provider at "https://provider.test/v1"
        And an archive item "article-1" with data
        """
        {"profile": "story", "language": "en", "body_html": "<p>The council met on Tuesday.</p>"}
        """
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "default_model": "openai/gpt-4o-mini"
        }
        """
        Then we get OK response
        When we post to "/ai_actions"
        """
        {
            "name": "Headline suggestions",
            "action_type": "suggestion",
            "input_fields": ["body_html"],
            "output_field": "headline",
            "provider": "#ai_providers._id#"
        }
        """
        Then we get OK response
        When we login as user "ai_configurator" with password "configurator123" and user type "user"
        """
        {"privileges": {"ai_studio": 1}}
        """
        And we get "/ai_actions/#ai_actions._id#"
        Then we get OK response
        When we run the AI action at "/ai_actions/#ai_actions._id#/run"
        """
        {"item_id": "article-1"}
        """
        Then we get error 403

    @auth
    Scenario: Managing actions needs the ai_studio privilege
        When we post to "/ai_providers"
        """
        {
            "name": "OpenRouter",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.test/v1",
            "default_model": "openai/gpt-4o-mini"
        }
        """
        Then we get OK response
        When we post to "/ai_actions"
        """
        {
            "name": "Headline suggestions",
            "action_type": "suggestion",
            "input_fields": ["body_html"],
            "output_field": "headline",
            "provider": "#ai_providers._id#"
        }
        """
        Then we get OK response
        When we login as user "ai_editor" with password "editor123" and user type "user"
        """
        {"privileges": {"ai": 1}}
        """
        And we get "/ai_actions"
        Then we get error 403
        When we get "/ai_actions/#ai_actions._id#"
        Then we get error 403
        When we post to "/ai_actions"
        """
        {
            "name": "Another action",
            "action_type": "summary",
            "input_fields": ["body_html"],
            "output_field": "abstract",
            "provider": "#ai_providers._id#"
        }
        """
        Then we get error 403

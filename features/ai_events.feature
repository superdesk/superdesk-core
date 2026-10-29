Feature: AI events

    @auth
    Scenario: A run writes an event describing it, without a copy of the article
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
        When we get "/ai_events"
        Then we get list with 1 items
        And we get existing resource
        """
        {"_items": [{
            "item_id": "article-1",
            "action_id": "#ai_actions._id#",
            "action_type": "suggestion",
            "provider_id": "#ai_providers._id#",
            "provider_type": "openai_compatible",
            "model_requested": "openai/gpt-4o-mini",
            "model_reported": "openai/gpt-4o-mini",
            "content_profile": "story",
            "language": "en",
            "source": "authoring",
            "status": "ok",
            "input_tokens": 42,
            "output_tokens": 7,
            "suggestions": ["Council votes on budget", "Council backs the budget", "Budget passes at the council"],
            "outcome": "pending"
        }]}
        """
        And we get "body_html" does not exist
        And we get "api_key" does not exist

    @auth
    Scenario: The user a run was made for reports what was done with its answers
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
        When we login as user "ai_editor" with password "editor123" and user type "user"
        """
        {"privileges": {"ai": 1}}
        """
        And we run the AI action at "/ai_actions/#ai_actions._id#/run"
        """
        {"item_id": "article-1"}
        """
        Then we get OK response
        And we store response as "ai_run"
        When we patch "/ai_events/#ai_run.event_id#" without an etag
        """
        {"outcome": "accepted", "applied_index": 1}
        """
        Then we get response code 200
        And we get existing resource
        """
        {"_id": "#ai_run.event_id#", "outcome": "accepted", "applied_index": 1, "outcome_at": "__any_value__"}
        """
        And we get "status" does not exist
        And we get "suggestions" does not exist

    @auth
    Scenario: Reporting an outcome on a run made for somebody else is refused
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
        When we login as user "ai_editor" with password "editor123" and user type "user"
        """
        {"privileges": {"ai": 1}}
        """
        And we run the AI action at "/ai_actions/#ai_actions._id#/run"
        """
        {"item_id": "article-1"}
        """
        Then we get OK response
        And we store response as "ai_run"
        When we login as user "other_ai_editor" with password "editor123" and user type "user"
        """
        {"privileges": {"ai": 1}}
        """
        And we patch "/ai_events/#ai_run.event_id#" without an etag
        """
        {"outcome": "accepted"}
        """
        Then we get error 403

    @auth
    Scenario: Reading the run log needs the ai_studio privilege
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
        When we login as user "ai_editor" with password "editor123" and user type "user"
        """
        {"privileges": {"ai": 1}}
        """
        And we run the AI action at "/ai_actions/#ai_actions._id#/run"
        """
        {"item_id": "article-1"}
        """
        Then we get OK response
        And we store response as "ai_run"
        When we get "/ai_events"
        Then we get error 403
        When we get "/ai_events/#ai_run.event_id#"
        Then we get error 403
        When we setup test user
        And we get "/ai_events"
        Then we get list with 1 items
        When we get "/ai_events/#ai_run.event_id#"
        Then we get OK response
        """
        {"item_id": "article-1", "outcome": "pending"}
        """

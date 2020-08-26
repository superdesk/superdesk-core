Feature: Localization

    @auth
    Scenario: Get timezones

        When we get "/locales/timezones"
        Then we get existing resource
        """
        {"timezones": [
            {
                "id": "America/Edmonton",
                "name": "Mountain Time",
                "location": "Canada (Edmonton) Time"
            }
        ]}
        """

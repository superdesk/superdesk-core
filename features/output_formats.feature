Feature: Output Formats

    @auth
    Scenario: Get list of available formats
        When we get "/output_formats"
        Then we get list with 1+ items
        """
        {"_items": [
            {"name": "NINJS", "type": "ninjs"},
            {"name": "NewsML G2", "type": "newsmlg2"}
        ]}
        """

Feature: Download with JWT Token Authentication

    Scenario: Download without token returns 401
        When we get "/download/test123"
        Then we get error 401
        """
        {"_message": "Token required"}
        """

    @auth
    Scenario: Export creates download URL with JWT token
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        Given "archive"
        """
        [{
            "guid": "item1",
            "type": "text",
            "headline": "Test",
            "slugline": "test-item",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
            "unique_id": 1
        }]
        """
        When we post to "/export"
        """
        {"item_ids": ["#archive._id#"], "format_type": "NINJSFormatter"}
        """
        Then we get new resource
        """
        {"url": "__any_value__"}
        """
        And we get download URL with token

    @auth
    Scenario: Download with valid JWT token succeeds without session
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        Given "archive"
        """
        [{
            "guid": "item1",
            "type": "text",
            "headline": "Test",
            "slugline": "test-item",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
            "unique_id": 1
        }]
        """
        When we post to "/export"
        """
        {"item_ids": ["#archive._id#"], "format_type": "NINJSFormatter"}
        """
        Then we get download URL with token
        Given I logout
        When we download the export URL with token
        Then we get response code 200

    Scenario: Download with invalid JWT token returns 401
        When we get "/download/test123?token=invalid_token"
        Then we get error 401
        """
        {"_message": "Invalid or expired token"}
        """

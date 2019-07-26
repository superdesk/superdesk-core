Feature: Related items

    @auth
    Scenario: Get related items
        Given "archive"
        """
        [
            {"_id": "original", "state": "published", "family_id": "original"},
            {"_id": "draft", "state": "draft", "family_id": "original"},
            {"_id": "published", "state": "published", "family_id": "original"},
            {"_id": "other", "state": "published", "family_id": "other"}
        ]
        """
        When we get "/archive/original/related?exclude=0"
        Then we get list with 2 items
        """
        {"_items": [
            {"_id": "original"},
            {"_id": "published"}
        ]}
        """

        When we get "/archive/original/related?exclude=1"
        Then we get list with 1 items
        """
        {"_items": [
            {"_id": "published"}
        ]}
        """

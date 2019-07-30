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
        When we get "/archive/original/related"
        Then we get list with 1 items
        """
        {"_items": [
            {"_id": "published"}
        ]}
        """
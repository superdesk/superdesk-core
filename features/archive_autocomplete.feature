Feature: Archive autocomplete

    @auth
    Scenario: Not enabled by default
        When we get "/archive_autocomplete?field=slugline&language=en"
        Then we get error 404

    @auth
    Scenario: Get distinct sluglines for published items
        Given config update
        """
        {
            "ARCHIVE_AUTOCOMPLETE": true,
            "ARCHIVE_AUTOCOMPLETE_DAYS": 9999
        }
        """
        Given "archive"
        """
        [
            {"slugline": "published", "state": "published", "versioncreated": "2019-01-01T00:00:00+0000"},
            {"slugline": "published_old", "state": "published", "versioncreated": "1919-01-01T00:00:00+0000"},
            {"slugline": "draft", "state": "draft", "versioncreated": "2019-01-01T00:00:00+0000"},
            {"slugline": "czech", "state": "published", "versioncreated": "2019-01-01T00:00:00+0000", "language": "cs"}
        ]
        """
        When we get "/archive_autocomplete?field=slugline&language=en"
        Then we get list with 1 items
        """
        {"_items": [
            {"value": "published"}
        ]}
        """
